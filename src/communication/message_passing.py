
import aiohttp
import asyncio

async def post_json(url, data):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=data, timeout=5) as r:
                if r.status==200:
                    return await r.json()
                return {}
    except:
        return {}
