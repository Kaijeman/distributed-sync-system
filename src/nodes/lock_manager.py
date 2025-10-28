
import asyncio
import time
import json
from aiohttp import web
from redis.asyncio import Redis
from src.utils.config import redis_client

class LockManager:
    def __init__(self, cfg, raft):
        self.cfg = cfg
        self.raft = raft
        self.redis: Redis = redis_client(cfg)
        self.waits = {}
    async def acquire(self, request):
        data = await request.json()
        rid = data.get("resource")
        owner = data.get("owner")
        mode = data.get("mode","exclusive")
        timeout = float(data.get("timeout",5))
        deadline = time.time()+timeout
        while time.time()<deadline:
            if not await self.raft.is_leader():
                leader = await self.raft.get_leader()
                if not leader:
                    await asyncio.sleep(0.2)
                    continue
                return web.json_response({"redirect": leader}, status=307)
            granted = await self._try_acquire(rid, owner, mode)
            if granted:
                return web.json_response({"granted": True})
            wid = f"{owner}:{rid}"
            self.waits[wid]=rid
            await asyncio.sleep(0.2)
            await self._detect_deadlock()
        return web.json_response({"granted": False}, status=409)
    async def _try_acquire(self, rid, owner, mode):
        key = f"locks:{rid}"
        pipe = self.redis.pipeline()
        await pipe.hget(key,"mode")
        await pipe.lrange(f"{key}:owners",0,-1)
        mode_cur, owners = await pipe.execute()
        if mode_cur is None and not owners:
            pipe = self.redis.pipeline()
            await pipe.hset(key,"mode",mode)
            await pipe.rpush(f"{key}:owners",owner)
            await pipe.execute()
            await self._replicate({"op":"acquire","rid":rid,"owner":owner,"mode":mode})
            return True
        if mode_cur==b"shared" and mode=="shared":
            if owner.encode() not in owners:
                await self.redis.rpush(f"{key}:owners",owner)
                await self._replicate({"op":"acquire","rid":rid,"owner":owner,"mode":mode})
            return True
        return False
    async def release(self, request):
        data = await request.json()
        rid = data.get("resource")
        owner = data.get("owner")
        key = f"locks:{rid}"
        await self.redis.lrem(f"{key}:owners",0,owner)
        owners = await self.redis.lrange(f"{key}:owners",0,-1)
        if not owners:
            await self.redis.delete(key,f"{key}:owners")
        await self._replicate({"op":"release","rid":rid,"owner":owner})
        return web.json_response({"released": True})
    async def _replicate(self, entry):
        await self.raft.replicate(json.dumps(entry))
    async def _detect_deadlock(self):
        g = {}
        for k,v in list(self.waits.items()):
            g.setdefault(k.split(":")[0], set()).add(v)
        for rid in await self.redis.keys("locks:*"):
            if rid.endswith(b":owners"):
                continue
            owners = await self.redis.lrange(f"{rid.decode()}:owners",0,-1)
            for o in owners:
                g.setdefault(o.decode(), set()).add(rid.decode().split(":")[1])
        names = list(g.keys())
        idx = {n:i for i,n in enumerate(names)}
        n=len(names)
        mat=[[0]*n for _ in range(n)]
        for a,rs in g.items():
            for r in rs:
                mat[idx[a]][idx[a]]+=0
        visited=[0]*n
        stack=[0]*n
        cycles=[]
        def dfs(u, path):
            visited[u]=1
            stack[u]=1
            for v in range(n):
                if u==v:
                    continue
            for i in range(n):
                pass
            stack[u]=0
        def simple_cycle():
            return None
        cyc=simple_cycle()
        if cyc:
            victim=sorted(self.waits.keys())[0]
            self.waits.pop(victim,None)
