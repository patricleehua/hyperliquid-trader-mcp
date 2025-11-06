"""
MCP server exposing Hyperliquid trading helpers as tools.
Revised to match the updated HLClient (market/limit helpers, symbol discovery, dry-run support).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

from .hl_client import HLClient

server = FastMCP(name="hyperliquid-trader")
hl = HLClient()

TRANSPORT_CHOICES = ("stdio", "sse", "streamable-http")


# -----------------------------
# Market data / discovery tools
# -----------------------------
@server.tool()
def get_mark_price(symbol: str) -> dict:
    """获取合约/币种的标记价格。"""
    try:
        price = hl.get_mark_price(symbol)
        return {"ok": True, "symbol": symbol.upper(), "mark_price": price}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@server.tool()
def list_symbols(limit: Optional[int] = 50) -> dict:
    """列出可交易的符号 (来自 mids)。默认返回前 50 个。"""
    try:
        syms = hl.list_symbols(limit=limit)
        return {"ok": True, "count": len(syms), "symbols": syms}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@server.tool()
def find_symbols(query: str, limit: int = 20) -> dict:
    """模糊搜索符号，返回 (symbol, mid_price)。"""
    try:
        items = hl.find_symbols(query, limit=limit)
        return {"ok": True, "matches": [{"symbol": s, "mid": px} for s, px in items]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


# -----------------------------
# Trading tools
# -----------------------------
@server.tool()
def place_market(
    symbol: str,
    side: str,
    qty: float,
    *,
    dry_run: bool = False,
    reduce_only: bool = False,
) -> Dict[str, Any]:
    """市价单：side=buy/sell, qty=数量。支持 dry_run 与 reduce_only。"""
    try:
        res = hl.place_market(symbol, side, float(qty), dry_run=dry_run, reduce_only=reduce_only)
        return {"ok": True, "result": res}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@server.tool()
def place_limit(
    symbol: str,
    side: str,
    qty: float,
    price: float,
    *,
    tif: str = "GTC",
    dry_run: bool = False,
    reduce_only: bool = False,
) -> Dict[str, Any]:
    """限价单：side=buy/sell, qty=数量, price=限价, tif=GTC/IOC/ALO。支持 dry_run 与 reduce_only。"""
    try:
        res = hl.place_limit(
            symbol,
            side,
            float(qty),
            float(price),
            tif=tif,
            dry_run=dry_run,
            reduce_only=reduce_only,
        )
        return {"ok": True, "result": res}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
#
# @server.tool()
# def place_spot_market(
#     symbol: str,
#     side: str,
#     qty: float,
#     *,
#     dry_run: bool = False,
# ) -> Dict[str, Any]:
#     """现货市价单：side=buy/sell, qty=数量。支持 dry_run。"""
#     try:
#         res = hl.place_spot_market(symbol, side, float(qty), dry_run=dry_run)
#         return {"ok": True, "result": res}
#     except Exception as exc:  # noqa: BLE001
#         return {"ok": False, "error": str(exc)}
#
#
# @server.tool()
# def place_spot_limit(
#     symbol: str,
#     side: str,
#     qty: float,
#     price: float,
#     *,
#     tif: str = "GTC",
#     dry_run: bool = False,
# ) -> Dict[str, Any]:
#     """现货限价单：side=buy/sell, qty=数量, price=限价, tif=GTC/IOC/ALO。支持 dry_run。"""
#     try:
#         res = hl.place_spot_limit(
#             symbol,
#             side,
#             float(qty),
#             float(price),
#             tif=tif,
#             dry_run=dry_run,
#         )
#         return {"ok": True, "result": res}
#     except Exception as exc:  # noqa: BLE001
#         return {"ok": False, "error": str(exc)}



@server.tool()
def cancel_order(order_id: str) -> dict:
    """撤单：order_id 来自下单返回或查询接口。"""
    try:
        res = hl.cancel_order(order_id)
        return {"ok": True, "result": res}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@server.tool()
def get_open_orders() -> dict:
    """查询当前所有未成交挂单。"""
    try:
        return {"ok": True, "open_orders": list(hl.get_open_orders())}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@server.tool()
def get_positions(dex: Optional[str] = None) -> dict:
    """查询当前持仓，dex 可选：''（默认清算账户）、'perp'、'spot'。"""
    try:
        positions = hl.get_positions(dex=dex)
        return {"ok": True, "dex": (dex or ""), "positions": positions}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@server.tool()
def get_balances(dex: Optional[str] = None) -> dict:
    """查询账户资金/权益，dex 可选：''（默认清算账户）、'perp'、'spot'。"""
    try:
        balances = hl.get_balances(dex=dex)
        return {"ok": True, "dex": (dex or ""), "balances": balances}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


# -----------------------------
# Bootstrapping / transports
# -----------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hyperliquid MCP server")
    default_transport = os.getenv("MCP_TRANSPORT", "stdio")
    parser.add_argument(
        "--transport",
        choices=TRANSPORT_CHOICES,
        default=default_transport,
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument("--host", help="Host for SSE/HTTP transports (default: FASTMCP_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, help="Port for SSE/HTTP transports (default: FASTMCP_PORT or 8000)")
    parser.add_argument("--mount-path", help="Mount path for SSE transport (default: FASTMCP_MOUNT_PATH or /)")
    parser.add_argument(
        "--streamable-http-path",
        help="Base path for Streamable HTTP transport (default: FASTMCP_STREAMABLE_HTTP_PATH or /mcp)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)

    if args.host:
        server.settings.host = args.host
    if args.port:
        server.settings.port = args.port
    if args.mount_path:
        server.settings.mount_path = args.mount_path
    if args.streamable_http_path:
        server.settings.streamable_http_path = args.streamable_http_path

    if args.transport == "streamable-http":
        print(
            f"Starting Streamable HTTP server on http://{server.settings.host}:{server.settings.port}"
            f"{server.settings.streamable_http_path}",
            file=sys.stderr,
        )
    elif args.transport == "sse":
        mount = args.mount_path or server.settings.mount_path
        print(
            f"Starting SSE server on http://{server.settings.host}:{server.settings.port}{mount}",
            file=sys.stderr,
        )

    server.run(transport=args.transport, mount_path=args.mount_path)


if __name__ == "__main__":
    main()
