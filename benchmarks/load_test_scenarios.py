
from locust import HttpUser, task, between
import random

class QueueLoad(HttpUser):
    wait_time = between(0.1,0.5)
    @task(3)
    def publish(self):
        self.client.post("/queue/publish", json={"topic":"t","data":{"x":random.randint(1,1000)}})
    @task(1)
    def consume(self):
        r=self.client.post("/queue/consume", json={"topic":"t","consumer":"c"}).json()
        if r.get("id"):
            self.client.post("/queue/ack", json={"topic":"t","id":r["id"]})
