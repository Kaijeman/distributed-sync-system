
import asyncio
import pytest
from src.nodes.cache_node import CacheNode
from src.utils.config import load_config

@pytest.mark.asyncio
async def test_cache_basic():
    cfg = load_config()
    c = CacheNode(cfg)
    class Req:
        def __init__(self, d): self._d=d
        async def json(self): return self._d
    await c.put(Req({"key":"k","value":{"v":1}}))
    res = await c.get(Req({"key":"k"}))
    assert res.status==200
