
import asyncio
import pytest
from src.nodes.queue_node import QueueNode
from src.utils.config import load_config

@pytest.mark.asyncio
async def test_queue_basic():
    cfg = load_config()
    q = QueueNode(cfg)
    class Req:
        def __init__(self, d): self._d=d
        async def json(self): return self._d
    await q.publish(Req({"topic":"t","data":{"x":1}}))
    res = await q.consume(Req({"topic":"t","consumer":"c"}))
    assert res.status==200
