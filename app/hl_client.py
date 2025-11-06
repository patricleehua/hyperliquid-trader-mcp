from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from eth_account import Account
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import (
    LOCAL_API_URL,
    MAINNET_API_URL,
    TESTNET_API_URL,
)

from .config import ACCOUNT_ADDRESS, API_BASE_URL, NETWORK, SECRET_KEY, SKIP_WEBSOCKET

# -----------------------------------------------------------------------------
# Public constants / aliases
# -----------------------------------------------------------------------------
TIF_ALIASES = {
    "GTC": "Gtc",
    "IOC": "Ioc",
    "ALO": "Alo",
}


class HLClient:
    """
    Thin, version-resilient wrapper around the Hyperliquid Python SDK.

    Goals:
      - Hide SDK version differences (mark price API names, constructor changes)
      - Provide safe helpers (symbol existence check, dry-run, input validation)
      - Keep MCP tools thin and predictable
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self) -> None:
        self.base_url = self._resolve_base_url(NETWORK, API_BASE_URL)
        self.wallet: LocalAccount = Account.from_key(SECRET_KEY)

        # Info: market/account reads. Exchange: trading ops.
        self.info = Info(base_url=self.base_url, skip_ws=SKIP_WEBSOCKET)
        self.exchange = Exchange(
            wallet=self.wallet,
            base_url=self.base_url,
            account_address=ACCOUNT_ADDRESS,
        )

    # ------------------------------------------------------------------
    # Market data helpers
    # ------------------------------------------------------------------
    def get_mark_price(self, symbol: str) -> float:
        """Return the latest mark price for `symbol` as float.
        Tries multiple SDK methods for compatibility; falls back to mids map.
        Raises AttributeError if no usable source is available.
        """
        symbol = symbol.strip().upper()
        fetchers = []
        if hasattr(self.info, "get_mark_price"):
            fetchers.append(self.info.get_mark_price)  # older name
        if hasattr(self.info, "mark_price"):
            fetchers.append(self.info.mark_price)      # newer name

        for getter in fetchers:
            try:
                raw_px = getter(symbol)
                return self._coerce_price(raw_px)
            except Exception:
                continue

        # Fallback: mids map
        mids = self._get_all_mids()
        if symbol in mids:
            return float(mids[symbol])

        fallback = self._fallback_mark_price(symbol)
        if fallback is not None:
            return fallback

        tried = ", ".join(f.__name__ for f in fetchers) or "no known mark price methods"
        raise AttributeError(
            "Hyperliquid Info client does not expose a usable mark price method "
            f"(tried: {tried}); and symbol '{symbol}' not found in mids."
        )

    def _get_all_mids(self) -> Dict[str, float]:
        """Return a {symbol -> mid price} dict, handling SDK naming."""
        for name in ("all_mids", "allMids"):
            f = getattr(self.info, name, None)
            if callable(f):
                mids = f() or {}
                # Normalize keys to uppercase
                return {str(k).upper(): float(v) for k, v in mids.items()}
        return {}

    def list_symbols(self, limit: Optional[int] = None) -> List[str]:
        """List available trading symbols (from mids)."""
        syms = sorted(self._get_all_mids().keys())
        return syms if limit is None else syms[:limit]

    def find_symbols(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        """Fuzzy search symbols containing `query` (case-insensitive).
        Returns list of (symbol, mid_price).
        """
        q = query.strip().lower()
        mids = self._get_all_mids()
        out: List[Tuple[str, float]] = []
        for s, px in mids.items():
            if q in s.lower():
                if 1 <= len(s) <= 12:  # filter noisy tickers
                    out.append((s, float(px)))
            if len(out) >= limit:
                break
        return out

    def ensure_symbol_exists(self, symbol: str) -> None:
        symbol = symbol.strip().upper()
        if symbol not in self._get_all_mids():
            raise ValueError(
                f"Symbol '{symbol}' not found in exchange mids; call list_symbols()/find_symbols() first."
            )

    # ------------------------------------------------------------------
    # Trading helpers (safe wrappers) - market & limit
    # ------------------------------------------------------------------
    def place_market(self,
        symbol: str,
        side: str,
        qty: float,
        *,
        dry_run: bool = False,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """Place a market order. When dry_run=True, returns the would-be payload."""
        symbol_u = symbol.strip().upper()
        self.ensure_symbol_exists(symbol_u)

        side_norm = side.strip().lower()
        if side_norm not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")
        size = self._to_float(qty, "qty")
        if size <= 0:
            raise ValueError("qty must be greater than 0")

        payload = {
            "name": symbol_u,
            "is_buy": side_norm == "buy",
            "sz": float(size),
            "order_type": {"mkt": {}},  # for visibility in dry-run
            "reduce_only": bool(reduce_only),
        }
        if dry_run:
            return {"dry_run": True, "request": payload}

        # SDK has dedicated helper for market
        return self.exchange.market_open(symbol_u, is_buy=payload["is_buy"], sz=payload["sz"])

    def place_limit(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        *,
        tif: str = "GTC",
        dry_run: bool = False,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """Place a limit order with TIF (GTC/IOC/ALO). When dry_run=True, only returns would-be payload."""
        symbol_u = symbol.strip().upper()
        self.ensure_symbol_exists(symbol_u)

        side_norm = side.strip().lower()
        if side_norm not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")

        size = self._to_float(qty, "qty")
        if size <= 0:
            raise ValueError("qty must be greater than 0")

        limit_px = self._to_float(price, "price")
        if limit_px <= 0:
            raise ValueError("price must be greater than 0 for limit orders")

        tif_wire = self._normalize_tif(tif)
        payload = {
            "name": symbol_u,
            "is_buy": side_norm == "buy",
            "sz": float(size),
            "limit_px": float(limit_px),
            "order_type": {"limit": {"tif": tif_wire}},
            "reduce_only": bool(reduce_only),
        }
        if dry_run:
            return {"dry_run": True, "request": payload}

        return self.exchange.order(**payload)

    # ------------------------------------------------------------------
    # Spot trading helpers (not yet supported by official SDK)
    # ------------------------------------------------------------------
    def place_spot_market(
        self,
        symbol: str,
        side: str,
        qty: float,
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Hyperliquid Python SDK does not expose spot market order helpers."
        )

    def place_spot_limit(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        *,
        tif: str = "GTC",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Hyperliquid Python SDK does not expose spot limit order helpers."
        )


    def cancel_order(self, oid: str | int) -> Dict[str, Any]:
        """Cancel an order by order id (looks up symbol via open orders)."""
        order_id = self._to_int(oid, "order_id")
        for order in self.get_open_orders():
            try:
                if int(order.get("oid")) == order_id:
                    return self.exchange.cancel(order["coin"], order_id)
            except Exception:
                continue
        raise ValueError(f"Order id {order_id} not found in open orders.")

    # ------------------------------------------------------------------
    # Account state helpers
    # ------------------------------------------------------------------
    def get_positions(self, *, dex: str | None = None) -> List[Dict[str, Any]]:
        """Return positions for the selected dex (e.g. '', 'perp', 'spot')."""
        state = self._fetch_user_state(dex)
        for key in (
            "assetPositions",
            "perpPositions",
            "assetPositionsPerps",
            "spotPositions",
        ):
            positions = state.get(key)
            if positions:
                return positions  # type: ignore[return-value]
        fallback = state.get("assetPositions")
        if isinstance(fallback, list):
            return fallback  # type: ignore[return-value]
        return []

    def get_balances(self, *, dex: str | None = None) -> Dict[str, Any]:
        """Return balance and margin information for the selected dex."""
        state = self._fetch_user_state(dex)
        return {
            "balances": state.get("balances") or [],
            "marginSummary": state.get("marginSummary"),
            "crossMarginSummary": state.get("crossMarginSummary"),
            "crossMaintenanceMarginUsed": state.get("crossMaintenanceMarginUsed"),
            "withdrawable": state.get("withdrawable"),
            "time": state.get("time"),
        }

    def get_open_orders(self) -> Iterable[Dict[str, Any]]:
        return self.info.open_orders(ACCOUNT_ADDRESS)

    # ------------------------------------------------------------------
    # Internals / utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_tif(tif: str) -> str:
        tif_key = tif.strip().upper()
        if tif_key not in TIF_ALIASES:
            supported = ", ".join(TIF_ALIASES)
            raise ValueError(f"Unsupported tif '{tif}'. Supported values: {supported}")
        return TIF_ALIASES[tif_key]

    @staticmethod
    def _resolve_base_url(network: str, override: Optional[str]) -> str:
        if override:
            return override
        normalized = network.lower()
        if normalized in {"mainnet", "main"}:
            return MAINNET_API_URL
        if normalized in {"testnet", "test"}:
            return TESTNET_API_URL
        if normalized in {"local", "localhost"}:
            return LOCAL_API_URL
        raise ValueError(
            f"Unsupported HL_NETWORK '{network}'. Set HL_API_BASE_URL to a custom endpoint if needed."
        )

    @staticmethod
    def _to_int(value: str | int, field: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be an integer, got {value!r}") from exc

    @staticmethod
    def _to_float(value: float | str, field: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be numeric, got {value!r}") from exc

    @staticmethod
    def _coerce_price(raw: Any) -> float:
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            return float(raw)
        if isinstance(raw, dict):
            for key in ("markPrice", "mark_price", "price", "px"):
                if key in raw:
                    return float(raw[key])
        if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
            for item in raw:
                try:
                    return HLClient._coerce_price(item)
                except (TypeError, ValueError):
                    continue
        raise ValueError(f"Unexpected mark price payload: {raw!r}")

    def _fetch_user_state(self, dex: Optional[str]) -> Dict[str, Any]:
        dex_value = (dex or "").strip()
        return self.info.user_state(ACCOUNT_ADDRESS, dex=dex_value)

    def _fallback_mark_price(self, symbol: str) -> Optional[float]:
        # Kept for compatibility with older SDKs exposing richer meta() trees.
        meta_call = getattr(self.info, "meta", None)
        if not callable(meta_call):
            return None
        try:
            meta = meta_call()
        except Exception:
            return None

        symbol_key = symbol.upper()
        containers: List[Any] = []
        if isinstance(meta, dict):
            containers = [meta, meta.get("universe"), meta.get("markets"), meta.get("assets")]
        else:
            containers = [meta]

        for container in containers:
            if isinstance(container, dict):
                maybe_px = self._extract_from_container(container, symbol_key)
                if maybe_px is not None:
                    return maybe_px
            elif isinstance(container, Iterable) and not isinstance(container, (str, bytes)):
                for item in container:
                    maybe_px = self._extract_from_container(item, symbol_key)
                    if maybe_px is not None:
                        return maybe_px
        return None

    @staticmethod
    def _extract_from_container(entry: Any, symbol_key: str) -> Optional[float]:
        if not isinstance(entry, dict):
            return None
        name_fields = ["symbol", "coin", "name", "ticker"]
        for field in name_fields:
            if field in entry and str(entry[field]).upper() == symbol_key:
                for price_key in ("markPx", "mark_price", "markPrice", "px", "price"):
                    if price_key in entry:
                        try:
                            return float(entry[price_key])
                        except (TypeError, ValueError):
                            return None
        return None
