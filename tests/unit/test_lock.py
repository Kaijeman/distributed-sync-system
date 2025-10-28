
import asyncio
import pytest
from src.nodes.lock_manager import LockManager
from src.consensus.raft import RaftNode
from src.utils.config import load_config

@pytest.mark.asyncio
async def test_lock_cycle():
    cfg = load_config()
    r = RaftNode(cfg)
    r.role="leader"
    lm = LockManager(cfg,r)
    class Req:
        def __init__(self, d): self._d=d
        async def json(self): return self._d
    ok = await lm.acquire(Req({"resource":"r1","owner":"a","mode":"exclusive"}))
    assert ok.status==200
