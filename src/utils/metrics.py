
from aiohttp import web
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

def setup_metrics(cfg):
    registry = CollectorRegistry()
    app = web.Application()
    async def metrics(request):
        data = generate_latest(registry)
        return web.Response(body=data, content_type=CONTENT_TYPE_LATEST)
    app.add_routes([web.get('/metrics', metrics)])
    return app
