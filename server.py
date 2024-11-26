import asyncio
import websockets
import aiofiles


async def echo(websocket):
    async with aiofiles.open("data.json", mode='r') as f:
        data = await f.read()
    await websocket.send(data)

async def main():
    server = await websockets.serve(echo, "0.0.0.0", 2333)
    await server.wait_closed()

asyncio.run(main())

