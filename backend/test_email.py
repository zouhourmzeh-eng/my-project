import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/api/auth/forgot-password", json={"email": "chadliakaouech@gmail.com"})
        print(res.status_code, res.text)

asyncio.run(test())
