import uvicorn
from fastapi import FastAPI, Request
from mcp.server import MCPServer
from mcp.server.sse import SseServerTransport

mcp = MCPServer("test")

@mcp.tool()
async def hello():
    return "world"

app = FastAPI()
sse = SseServerTransport("/messages")

@app.get("/sse")
async def handle_sse(request: Request):
    print(f"Method: {request.scope['method']}")
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp._lowlevel_server.create_initialization_options())

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    uvicorn.run(app, port=8002)
