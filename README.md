# SGraph MCP Server

## Install dependencies

```bash
uv sync
```

## Run the server

```bash
uv run src/server.py
```

## MCP client configuration

```json
{
  "mcpServers": {
    "sgraph-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/sse"]
    }
  }
}
```
