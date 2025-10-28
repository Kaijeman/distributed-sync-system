# Distributed Sync System — Demo & Testing (Windows CMD)

Dokumen ini berisi **semua langkah demo dan testing** untuk proyek. Semua perintah ditulis untuk **Windows CMD**.  
Gunakan `curl.exe` dan JSON dengan **double quotes** lalu escape tanda kutip di dalam JSON seperti `"{\"key\":\"v\"}"`.

---

## Prasyarat
- Docker + Docker Compose v2
- Windows 10/11
- (Opsional) Python 3.11 untuk `pytest` & `locust` di host

> Port yang digunakan: `8001–8003` (API), `9001–9003` (metrics), `6379` (Redis). Pastikan kosong.

---

## 0) Start bersih, build, dan jalankan cluster
```cmd
docker compose -f docker\docker-compose.yml down -v && docker compose -f docker\docker-compose.yml build --no-cache && docker compose -f docker\docker-compose.yml up -d
```

## 1) Cek health & status Raft
```cmd
docker compose -f docker\docker-compose.yml ps && curl.exe http://localhost:8001/health && curl.exe http://localhost:8002/health && curl.exe http://localhost:8003/health && curl.exe http://localhost:8001/raft/state
```

---

## 2) DEMO QUEUE — publish → consume → ACK
Kita reset topik `t`, seed 1 pesan stabil, lalu `consume` & `ACK` **tanpa** menyalin ID (ID tetap: `dad11f12fd336e4d87ebd58c6aaa2579`).

```cmd
docker compose -f docker\docker-compose.yml exec redis sh -c "redis-cli DEL q:t q:inflight:t >/dev/null && redis-cli RPUSH q:t '{\"ts\":0,\"data\":{\"x\":1}}' >/dev/null && redis-cli TYPE q:t && redis-cli LLEN q:t"
```
```cmd
curl.exe -X POST http://localhost:8002/queue/consume -H "Content-Type: application/json" -d "{\"topic\":\"t\",\"consumer\":\"c1\"}"
```
```cmd
curl.exe -X POST http://localhost:8002/queue/ack -H "Content-Type: application/json" -d "{\"topic\":\"t\",\"id\":\"dad11f12fd336e4d87ebd58c6aaa2579\"}"
```

---

## 3) DEMO LOCK — exclusive & shared
```cmd
curl.exe -X POST http://localhost:8001/lock/acquire -H "Content-Type: application/json" -d "{\"resource\":\"r1\",\"owner\":\"alice\",\"mode\":\"exclusive\"}"
```
```cmd
curl.exe -X POST http://localhost:8002/lock/acquire -H "Content-Type: application/json" -d "{\"resource\":\"r1\",\"owner\":\"bob\",\"mode\":\"exclusive\",\"timeout\":2}"
```
```cmd
curl.exe -X POST http://localhost:8001/lock/release -H "Content-Type: application/json" -d "{\"resource\":\"r1\",\"owner\":\"alice\"}"
```
```cmd
curl.exe -X POST http://localhost:8001/lock/acquire -H "Content-Type: application/json" -d "{\"resource\":\"r2\",\"owner\":\"u1\",\"mode\":\"shared\"}"
```
```cmd
curl.exe -X POST http://localhost:8002/lock/acquire -H "Content-Type: application/json" -d "{\"resource\":\"r2\",\"owner\":\"u2\",\"mode\":\"shared\"}"
```

---

## 4) DEMO CACHE — put → get → invalidate → get ulang
```cmd
curl.exe -X POST http://localhost:8001/cache/put -H "Content-Type: application/json" -d "{\"key\":\"k\",\"value\":{\"x\":1}}"
```
```cmd
curl.exe -X POST http://localhost:8002/cache/get -H "Content-Type: application/json" -d "{\"key\":\"k\"}"
```
```cmd
curl.exe -X POST http://localhost:8003/cache/invalidate -H "Content-Type: application/json" -d "{\"key\":\"k\"}"
```
```cmd
curl.exe -X POST http://localhost:8002/cache/get -H "Content-Type: application/json" -d "{\"key\":\"k\"}"
```

---

## 5) DEMO FAILOVER ringan
```cmd
docker compose -f docker\docker-compose.yml stop node1 && curl.exe http://localhost:8002/raft/state && curl.exe -X POST http://localhost:8003/queue/publish -H "Content-Type: application/json" -d "{\"topic\":\"t\",\"data\":{\"x\":3}}" && docker compose -f docker\docker-compose.yml start node1
```

---

## 6) Metrics (opsional)
```cmd
curl.exe http://localhost:9001/metrics
```

---

## 7) TESTING OTOMATIS — Pytest (host Windows)
### 7.1 Siapkan environment
```cmd
py -3 -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt && .\.venv\Scripts\pip install pytest-asyncio
```
### 7.2 Jalankan pytest (gunakan Redis lokal & pastikan package `src` terdeteksi)
```cmd
set PYTHONPATH=%CD% && set REDIS_URL=redis://localhost:6379/0 && .\.venv\Scripts\pytest -q
```
> Jika pernah ada sisa lock dari demo, bersihkan terlebih dulu:
```cmd
docker compose -f docker\docker-compose.yml exec redis redis-cli DEL locks:r1 locks:r1:owners
```

---

## 8) PERFORMANCE TEST — Locust (headless)
```cmd
.\.venv\Scripts\locust -f benchmarks\load_test_scenarios.py --headless --host http://localhost:8001 -u 50 -r 5 -t 1m
```
> Perhatikan ringkasan: **req/s**, **avg/median**, dan **p95/p99**. Pada uji contoh, agregat sekitar **133 req/s** dengan median latensi ~**44 ms** dan error **0%**.

---

## 9) Troubleshooting cepat
- **Windows CMD & JSON**: selalu pakai `curl.exe` dan escape `"` → `"{\"key\":\"v\"}"`.
- **HTTP 500 saat consume**: reset queue `q:t` → `redis-cli DEL q:t q:inflight:t` lalu seed ulang.
- **409 pada test lock**: ada sisa key `locks:r1` → hapus atau gunakan DB Redis lain untuk test.
- **ModuleNotFoundError: src**: jalankan pytest dengan `set PYTHONPATH=%CD%`.
- **Container keluar cepat**: rebuild image terbaru → `docker compose build --no-cache && docker compose up -d`.
- **Lihat log**: `docker compose -f docker\docker-compose.yml logs --tail=200 node1`.

---

## 10) Stop & bersihkan
```cmd
docker compose -f docker\docker-compose.yml down -v
```

---

Link YouTube: https://youtu.be/VkzmLD67E2I?si=hrrkmKZxto4ezDee
