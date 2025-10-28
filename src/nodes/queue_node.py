
import asyncio
import hashlib
import json
import time
from aiohttp import web
from redis.asyncio import Redis
from src.utils.config import redis_client

class ConsistentHash:
    def __init__(self, nodes, replicas=50):
        self.ring = {}
        self.sorted_keys = []
        self.replicas = replicas
        self.nodes = nodes
        for n in nodes:
            for i in range(replicas):
                k = hashlib.md5(f"{n}:{i}".encode()).hexdigest()
                self.ring[k]=n
                self.sorted_keys.append(k)
        self.sorted_keys.sort()
    def get(self, key):
        if not self.ring:
            return None
        h = hashlib.md5(key.encode()).hexdigest()
        for k in self.sorted_keys:
            if h<=k:
                return self.ring[k]
        return self.ring[self.sorted_keys[0]]

class QueueNode:
    def __init__(self, cfg):
        self.cfg = cfg
        self.redis: Redis = redis_client(cfg)
        self.hash = ConsistentHash(cfg["PEERS"]+[cfg["SELF_URL"]])
    async def publish(self, request):
        data = await request.json()
        topic = data.get("topic","default")
        msg = json.dumps({"ts":time.time(),"data":data.get("data")})
        node = self.hash.get(topic)
        if node==self.cfg["SELF_URL"]:
            await self.redis.rpush(f"q:{topic}", msg)
            return web.json_response({"ok": True,"owned":True})
        return web.json_response({"redirect": node}, status=307)
    async def consume(self, request):
        data = await request.json()
        topic = data.get("topic","default")
        cid = data.get("consumer","c")
        m = await self.redis.lpop(f"q:{topic}")
        if not m:
            return web.json_response({"message": None})
        mid = hashlib.md5((m.decode()+cid).encode()).hexdigest()
        await self.redis.hset(f"q:inflight:{topic}", mid, m)
        await self.redis.expire(f"q:inflight:{topic}", 60)
        return web.json_response({"id": mid, "message": json.loads(m)})
    async def ack(self, request):
        data = await request.json()
        topic = data.get("topic","default")
        mid = data.get("id")
        await self.redis.hdel(f"q:inflight:{topic}", mid)
        return web.json_response({"ack": True})
