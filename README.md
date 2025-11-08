# [中文🇨🇳](https://github.com/patricleehua/hyperliquid-trader-mcp/blob/main/doc/README_CN.md)

# Hyperliquid MCP Trader

A trading toolchain built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).  
It wraps commonly used [Hyperliquid Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk) endpoints and exposes them as MCP tools:

- `get_mark_price(symbol)`: fetch the latest mark price  
- `place_omarket/limit(symbol, side, qty, price, tif)`: place a market or limit order  
- `place_spot_market/limit(...)`: spot entry points (not yet implemented in the current Hyperliquid SDK; calls raise `NotImplementedError`)  
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
> Optional variables: `HL_API_BASE_URL` (custom endpoint), `HL_SKIP_WS` (set to true to skip WebSocket), `MCP_AUTH_HEADER_VALUE` (shared secret that must appear in the `Authorization` header), `MCP_AUTH_HEADER_NAME` (override header name; defaults to `Authorization`).

## 2. Run the MCP Server

```bash
uv run --env-file .env python -m app.mcp_server
```

The `.env` file is optional. If it exists the loader grabs it automatically, but you can omit the `--env-file` flag entirely and provide the credentials as environment variables:

```bash
HL_ACCOUNT_ADDRESS=0xYourMainWalletAddress \
HL_SECRET_KEY=0xYourApiWalletPrivateKey \
HL_NETWORK=testnet \
uv run python -m app.mcp_server --transport streamable-http --host 0.0.0.0 --port 9000
```

Typical MCP host entry (pseudo JSON):
> Cherry Studio
```json
{
  "mcpServers": {
    "hyperliquid-trading": {
      "isActive": true,
      "name": "hyperliquid-trading",
      "type": "streamableHttp",
      "description": "hyperliquid-trading",
      "baseUrl": " http://0.0.0.0:9000/mcp",
      "headers": {
        "Authorization": "Bearer your-shared-secret"
      }
    }
  }
}
```

By default the server speaks over stdin/stdout, which is ideal for local development.  
To integrate with an MCP host (e.g., Claude Desktop, OpenAI Agents), register the same command in the host config.  
Alternatively activate `.venv` manually and run `python -m app.mcp_server`.

To host over HTTP or SSE, specify the transport and network parameters:

```bash
# Streamable HTTP (defaults to 127.0.0.1:8000/mcp)
uv run python -m app.mcp_server --transport streamable-http --host 0.0.0.0 --port 9000

# SSE (works with OpenAI Agents, default mount path /sse)
uv run python -m app.mcp_server --transport sse
```

Environment variables are also supported: `MCP_TRANSPORT=streamable-http`, `FASTMCP_HOST`, `FASTMCP_PORT`, etc.

When `MCP_AUTH_HEADER_VALUE` is set, every HTTP/SSE request must include the configured header/value pair (defaults to `Authorization:Bearer <value>`); leaving it empty disables the check.

### Request header validation

1. Set a shared secret: `export MCP_AUTH_HEADER_VALUE=super-secret-token`.  
2. (Optional) override the header name: `export MCP_AUTH_HEADER_NAME=X-Custom-Auth`.  
3. Restart the server. Any HTTP/SSE request that omits the header will receive `403 Missing or invalid request header`.

Example Streamable HTTP call:

```bash
curl -H "Authorization: super-secret-token" \
     -H "Content-Type: application/json" \
     -d '{"method":"list_tools","params":{}}' \
     http://127.0.0.1:8000/mcp
```

Clear `MCP_AUTH_HEADER_VALUE` (or unset it) if you want to disable the guard for local testing.

### Docker deployment

**Option A – build locally**

```bash
docker build -t hl-mcp .
docker run --rm \
  -e HL_ACCOUNT_ADDRESS=0xYourMainWalletAddress \
  -e HL_SECRET_KEY=0xYourApiWalletPrivateKey \
  -e HL_NETWORK=testnet \
  -e MCP_AUTH_HEADER_VALUE=super-secret-token \
  -p 9000:9000 \
  hl-mcp
```

**Option B – pull the prebuilt image**

```bash
docker pull patricleee/hyperliquid-trading-mcp:1.0.0
docker run --rm \
  -e HL_ACCOUNT_ADDRESS=0xYourMainWalletAddress \
  -e HL_SECRET_KEY=0xYourApiWalletPrivateKey \
  -e HL_NETWORK=testnet \
  -e MCP_AUTH_HEADER_VALUE=super-secret-token \
  -p 9000:9000 \
  patricleee/hyperliquid-trading-mcp:1.0.0
```

**Option C – Docker Compose**

A ready-to-use `docker-compose.yml` is included at the project root. Populate `.env` (same keys as usual) and launch:

```bash
cp .env.example .env  # edit the values first
docker compose -f docker-compose.yml up -d
```

## 3. Troubleshooting

- Ensure `HL_ACCOUNT_ADDRESS` and `HL_SECRET_KEY` match the chosen network (`HL_NETWORK`).  
- For rate limits (429) or timeouts, add retry/limit logic inside `HLClient`.  
- Always test on the testnet first; switch to mainnet only after validating the workflow.

---

The project structure follows patterns from Hyperliquid’s official/community SDK samples and the MCP Python SDK documentation.

[HyperLiquid DEX](https://hyperfoundation.org)

[What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/docs/getting-started/intro)
