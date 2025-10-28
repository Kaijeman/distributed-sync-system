import asyncio
import os
import json
from aiohttp import web
from src.utils.config import load_config
from src.utils.metrics import setup_metrics
from src.consensus.raft import RaftNode
from src.nodes.lock_manager import LockManager
from src.nodes.queue_node import QueueNode
from src.nodes.cache_node import CacheNode

class AppNode:
    def __init__(self):
        self.cfg = load_config()
        self.app = web.Application()
        self.raft = RaftNode(self.cfg)
        self.lock = LockManager(self.cfg, self.raft)
        self.queue = QueueNode(self.cfg)
        self.cache = CacheNode(self.cfg)
        self.metrics_app = setup_metrics(self.cfg)
    async def start(self):
        self.app.add_routes([web.get('/health', self.health)])
        self.app.add_routes([web.post('/raft/request_vote', self.raft.request_vote)])
        self.app.add_routes([web.post('/raft/append', self.raft.append_entries)])
        self.app.add_routes([web.get('/raft/state', self.raft.get_state)])
        self.app.add_routes([web.post('/lock/acquire', self.lock.acquire)])
        self.app.add_routes([web.post('/lock/release', self.lock.release)])
        self.app.add_routes([web.post('/queue/publish', self.queue.publish)])
        self.app.add_routes([web.post('/queue/consume', self.queue.consume)])
        self.app.add_routes([web.post('/queue/ack', self.queue.ack)])
        self.app.add_routes([web.post('/cache/put', self.cache.put)])
        self.app.add_routes([web.post('/cache/get', self.cache.get)])
        self.app.add_routes([web.post('/cache/invalidate', self.cache.invalidate)])
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=int(self.cfg["HTTP_PORT"]))
        await site.start()
        metrics_runner = web.AppRunner(self.metrics_app)
        await metrics_runner.setup()
        metrics_site = web.TCPSite(metrics_runner, host="0.0.0.0", port=int(self.cfg["METRICS_PORT"]))
        await metrics_site.start()
        await self.raft.start()
        await self.cache.start()
        while True:
            await asyncio.sleep(1)
    async def health(self, request):
        return web.json_response({"ok": True, "node": self.cfg["NODE_ID"]})

def main():
    node = AppNode()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(node.start())

if __name__ == '__main__':
    main()
