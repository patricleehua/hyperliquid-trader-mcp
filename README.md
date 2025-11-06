# [中文🇨🇳](https://github.com/patricleehua/hyperliquid-trader-mcp/blob/main/doc/README_CN.md)

# Hyperliquid MCP Trader

A trading toolchain built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).  
It wraps commonly used Hyperliquid Python SDK endpoints and exposes them as MCP tools:

- `get_mark_price(symbol)`: fetch the latest mark price  
- `place_order(symbol, side, qty, price, tif)`: place a market or limit order  
- `place_spot_market/limit/order(...)`: spot entry points (not yet implemented in the current Hyperliquid SDK; calls raise `NotImplementedError`)  
- `cancel_order(order_id)`: cancel an order by id  
- `get_positions(dex)`: return current positions (`dex` can be empty, `perp`, or `spot`)  
- `get_balances(dex)`: return balances and margin summaries (same `dex` options as above)

## 1. Environment Setup

1. Install [uv](https://github.com/astral-sh/uv) (`pip install uv` or follow the upstream guide).  
2. Create a virtual environment at the project root and sync dependencies:
   ```bash
   uv venv
   uv sync
   ```
   > Prefer manual installs? Run `uv pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` (or export variables manually) and fill in real credentials:
   ```bash
   cp .env.example .env
   # Edit .env:
   # HL_ACCOUNT_ADDRESS=0xYourMainWalletAddress
   # HL_SECRET_KEY=0xYourApiWalletPrivateKey
   # HL_NETWORK=testnet  # or mainnet
   ```

> **Security tip:** use Hyperliquid’s API wallet (trading permission only) and never commit real private keys.  
> Optional variables: `HL_API_BASE_URL` (custom endpoint), `HL_SKIP_WS` (set to true to skip WebSocket).

## 2. Run the MCP Server

```bash
uv run --env-file .env python -m app.mcp_server
```

By default the server speaks over stdin/stdout, which is ideal for local development.  
To integrate with an MCP host (e.g., Claude Desktop, OpenAI Agents), register the same command in the host config.  
Alternatively activate `.venv` manually and run `python -m app.mcp_server`.

To host over HTTP or SSE, specify the transport and network parameters:

```bash
# Streamable HTTP (defaults to 127.0.0.1:8000/mcp)
uv run --env-file .env python -m app.mcp_server --transport streamable-http --host 0.0.0.0 --port 9000

# SSE (works with OpenAI Agents, default mount path /sse)
uv run --env-file .env python -m app.mcp_server --transport sse
```

Environment variables are also supported: `MCP_TRANSPORT=streamable-http`, `FASTMCP_HOST`, `FASTMCP_PORT`, etc.

## 3. Troubleshooting

- Ensure `HL_ACCOUNT_ADDRESS` and `HL_SECRET_KEY` match the chosen network (`HL_NETWORK`).  
- For rate limits (429) or timeouts, add retry/limit logic inside `HLClient`.  
- Always test on the testnet first; switch to mainnet only after validating the workflow.

---

The project structure follows patterns from Hyperliquid’s official/community SDK samples and the MCP Python SDK documentation.
