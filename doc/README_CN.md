# Hyperliquid MCP Trader

一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 的交易工具集成，封装了 Hyperliquid 官方 Python SDK 的常用交易接口，并以 MCP 工具的形式对外提供：

- `get_mark_price(symbol)`：查询标记价格  
- `place_order(symbol, side, qty, price, tif)`：限价/市价下单  
- `place_spot_market/limit/order(...)`：现货下单入口（当前 SDK 暂不支持，调用会返回未实现错误）  
- `cancel_order(order_id)`：撤销订单  
- `get_positions(dex)`：查询当前持仓（dex 可选：空字符串、`perp`、`spot`）  
- `get_balances(dex)`：查询账户资金/权益（同上，附带保证金汇总）

## 1. 环境准备

1. 安装 [uv](https://github.com/astral-sh/uv)（`pip install uv` 或参照官方文档）  
2. 在项目根目录创建虚拟环境并同步依赖：
   ```bash
   uv venv
   uv sync
   ```
   > 如果更习惯手动安装，也可以执行 `uv pip install -r requirements.txt`。
3. 复制 `.env.example` 为 `.env`（或直接导出环境变量），填入真实信息：
   ```bash
   cp .env.example .env
   # 编辑 .env，填入：
   # HL_ACCOUNT_ADDRESS=0xYourMainWalletAddress
   # HL_SECRET_KEY=0xYourApiWalletPrivateKey
   # HL_NETWORK=testnet  # 或 mainnet
   ```

> **安全提示：** 建议使用 Hyperliquid 的 API Wallet（仅限交易权限），不要在代码库中保存真实私钥。
> 可选变量：`HL_API_BASE_URL`（自定义节点）、`HL_SKIP_WS`（置为 true 可跳过 WebSocket 连接）。

## 2. 运行 MCP 服务器

```bash
uv run --env-file .env python -m app.mcp_server
```

默认以 stdin/stdout 模式运行，适合本地联调。若要集成到支持 MCP 的宿主（如 Claude Desktop、OpenAI Agents），在宿主的 MCP 配置中新增该命令即可；也可以手动激活 `.venv` 后运行 `python -m app.mcp_server`。

需要 HTTP/SSE 部署时，可指定传输方式及网络参数，例如：

```bash
# Streamable HTTP（默认监听 127.0.0.1:8000/mcp）
uv run --env-file .env python -m app.mcp_server --transport streamable-http --host 0.0.0.0 --port 9000

# SSE（可配合 OpenAI Agents） 127.0.0.1:8000/sse
uv run --env-file .env python -m app.mcp_server --transport sse
```

也可以通过环境变量控制：`MCP_TRANSPORT=streamable-http`、`FASTMCP_HOST`、`FASTMCP_PORT` 等。

## 3. 问题排查

- 确认 `HL_ACCOUNT_ADDRESS` 与 `HL_SECRET_KEY` 已正确配置，并与所选网络（`HL_NETWORK`）一致  
- 遇到 429/超时等错误，可在 `HLClient` 中增加重试或限流  
- 调试时建议先在 testnet 完成自测，再切换到 mainnet

---

项目骨架参考自 Hyperliquid 官方/社区 SDK 示例与 MCP Python SDK 文档。
