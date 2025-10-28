
import os
from redis.asyncio import Redis

def load_config():
    node_id = os.getenv("NODE_ID","n0")
    http_port = int(os.getenv("HTTP_PORT","8000"))
    metrics_port = int(os.getenv("METRICS_PORT","9000"))
    peers = [p for p in os.getenv("PEERS","").split(",") if p]
    self_url = os.getenv("SELF_URL",f"http://localhost:{http_port}")
    cluster = os.getenv("CLUSTER_NAME","cluster")
    redis_url = os.getenv("REDIS_URL","redis://redis:6379/0")
    quorum = int(os.getenv("QUORUM", str(2)))
    return {"NODE_ID":node_id,"HTTP_PORT":http_port,"METRICS_PORT":metrics_port,"PEERS":peers,"SELF_URL":self_url,"CLUSTER":cluster,"REDIS_URL":redis_url,"QUORUM":quorum}
def redis_client(cfg):
    return Redis.from_url(cfg["REDIS_URL"], decode_responses=False)
