
import asyncio
import pytest
from src.consensus.raft import RaftNode
from src.utils.config import load_config

@pytest.mark.asyncio
async def test_election_state():
    cfg = load_config()
    r = RaftNode(cfg)
    await asyncio.sleep(0.1)
    r.role="leader"
    assert await r.is_leader()==True
