import asyncio
import json
import random
import time
from aiohttp import web
from src.communication.message_passing import post_json

class RaftNode:
    def __init__(self, cfg):
        self.cfg = cfg
        self.node_id = cfg["NODE_ID"]
        self.term = 0
        self.voted_for = None
        self.log = []
        self.commit_index = -1
        self.role = "follower"
        self.leader = None
        self.last_heartbeat = time.time()
        self.election_task = None
    async def start(self):
        if not self.election_task:
            self.election_task = asyncio.create_task(self.election_loop())
    async def election_loop(self):
        while True:
            t = random.uniform(1.2,2.4)
            await asyncio.sleep(0.2)
            if time.time()-self.last_heartbeat>t and self.role!="leader":
                await self.start_election()
    async def start_election(self):
        self.term+=1
        self.voted_for=self.node_id
        self.role="candidate"
        votes=1
        tasks=[]
        for p in self.cfg["PEERS"]:
            tasks.append(post_json(p+"/raft/request_vote",{"term":self.term,"candidate":self.cfg["SELF_URL"],"last_index":len(self.log)-1}))
        res = await asyncio.gather(*tasks, return_exceptions=True)
        for r in res:
            if isinstance(r, dict) and r.get("vote_granted"):
                votes+=1
        if votes>=self.cfg["QUORUM"]:
            self.role="leader"
            self.leader=self.cfg["SELF_URL"]
            asyncio.create_task(self.heartbeat_loop())
    async def heartbeat_loop(self):
        while self.role=="leader":
            await self.broadcast_append({"op":"noop"})
            await asyncio.sleep(0.5)
    async def request_vote(self, request):
        data = await request.json()
        term = data["term"]
        if term>self.term:
            self.term=term
            self.voted_for=None
            self.role="follower"
        grant=False
        if self.voted_for in [None, data["candidate"]] and term>=self.term:
            grant=True
            self.voted_for=data["candidate"]
        return web.json_response({"term":self.term,"vote_granted":grant})
    async def append_entries(self, request):
        data = await request.json()
        self.last_heartbeat=time.time()
        self.role="follower"
        self.leader=data.get("leader",self.leader)
        entry=data.get("entry")
        if entry:
            self.log.append(entry)
            self.commit_index=len(self.log)-1
        return web.json_response({"ok": True})
    async def get_state(self, request):
        return web.json_response({"role":self.role,"term":self.term,"leader":self.leader})
    async def is_leader(self):
        return self.role=="leader"
    async def get_leader(self):
        return self.leader
    async def broadcast_append(self, entry):
        tasks=[]
        for p in self.cfg["PEERS"]:
            tasks.append(post_json(p+"/raft/append",{"leader":self.cfg["SELF_URL"],"entry":entry}))
        await asyncio.gather(*tasks, return_exceptions=True)
    async def replicate(self, entry_str):
        if not await self.is_leader():
            return
        await self.broadcast_append({"op":"log","data":entry_str})
