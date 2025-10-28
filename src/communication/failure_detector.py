
import asyncio
import time
from src.communication.message_passing import post_json

class Heartbeat:
    def __init__(self, cfg):
        self.cfg=cfg
        self.status={p:0 for p in cfg["PEERS"]}
    async def run(self):
        while True:
            tasks=[]
            for p in self.cfg["PEERS"]:
                tasks.append(post_json(p+"/health",{}))
            res=await asyncio.gather(*tasks, return_exceptions=True)
            for i,p in enumerate(self.cfg["PEERS"]):
                self.status[p]=1 if isinstance(res[i],dict) and res[i].get("ok") else 0
            await asyncio.sleep(1)
