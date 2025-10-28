import time
import asyncio
import json
from aiohttp import web
from redis.asyncio import Redis
from src.utils.config import redis_client

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.store = {}
        self.order = []
    def get(self, k):
        if k in self.store:
            self.order.remove(k)
            self.order.append(k)
            return self.store[k][0]
        return None
    def put(self, k, v, state):
        if k in self.store:
            self.order.remove(k)
        elif len(self.store)>=self.capacity:
            ev=self.order.pop(0)
            del self.store[ev]
        self.store[k]=(v,state)
        self.order.append(k)
    def invalidate(self, k):
        if k in self.store:
            self.order.remove(k)
            del self.store[k]

class CacheNode:
    def __init__(self, cfg):
        self.cfg = cfg
        self.redis: Redis = redis_client(cfg)
        self.cache = LRUCache(128)
        self.state = {}
        self.channel = f"cache:{cfg['CLUSTER']}"
        self.task = None
    async def start(self):
        if not self.task:
            self.task = asyncio.create_task(self.listen())
    async def listen(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel)
        async for m in pubsub.listen():
            if m["type"]=="message":
                data=json.loads(m["data"].decode())
                if data["op"]=="invalidate":
                    self.cache.invalidate(data["key"])
    async def put(self, request):
        data = await request.json()
        k = data["key"]
        v = data["value"]
        self.cache.put(k,v,"M")
        await self.redis.set(f"cache:{k}", json.dumps(v))
        await self.redis.publish(self.channel, json.dumps({"op":"invalidate","key":k}))
        return web.json_response({"ok": True})
    async def get(self, request):
        data = await request.json()
        k = data["key"]
        v = self.cache.get(k)
        if v is None:
            raw = await self.redis.get(f"cache:{k}")
            if raw:
                v = json.loads(raw.decode())
                self.cache.put(k,v,"S")
        return web.json_response({"value": v})
    async def invalidate(self, request):
        data = await request.json()
        k = data["key"]
        self.cache.invalidate(k)
        await self.redis.delete(f"cache:{k}")
        await self.redis.publish(self.channel, json.dumps({"op":"invalidate","key":k}))
        return web.json_response({"ok": True})
