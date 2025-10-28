# Deployment Guide — Distributed Sync System

Dokumen ini menjelaskan cara men-deploy, menjalankan demo, serta menguji sistem pada lingkungan **Windows (CMD)** dan Linux/macOS.

> **Ringkas:** Sistem terdiri dari 3 node Python (HTTP/aiohttp) + 1 Redis. Orkestrasi via **Docker Compose**. Konfigurasi lewat environment atau file `.env`.

---

## 1) Prasyarat
- Docker & Docker Compose v2
- Port bebas: `8001–8003` (API), `9001–9003` (metrics), `6379` (Redis)
- (Opsional) Python 3.11 untuk menjalankan `pytest` dan `locust` di host

---

## 2) Struktur Proyek (ringkas)
```
distributed-sync-system/
├─ src/                # kode utama: nodes, consensus, communication, utils
├─ tests/              # pytest (unit, integration)
├─ docker/             # Dockerfile.node, docker-compose.yml
├─ benchmarks/         # locustfile (load test)
├─ docs/               # docs & API spec
├─ requirements.txt    # dependensi
└─ .env.example        # contoh konfigurasi
```

---

## 3) Konfigurasi Lingkungan

### 3.1 Variabel Utama
- `NODE_ID`           : id node, mis. `node1`
- `SELF_URL`          : URL HTTP untuk node ini, mis. `http://node1:8001`
- `PEERS`             : daftar URL peer (dipisahkan koma)
- `QUORUM`            : jumlah minimal suara untuk leader (mis. 2 pada 3 node)
- `HTTP_PORT`         : port servis HTTP (8001/8002/8003)
- `METRICS_PORT`      : port metrics (9001/9002/9003)
- `REDIS_URL`         : URL Redis (mis. `redis://redis:6379/0`)

> Salin `.env.example` menjadi `.env` bila ingin menyesuaikan nilai.

### 3.2 File `.env` (contoh ringkas)
```
REDIS_URL=redis://redis:6379/0
QUORUM=2
```

---

## 4) Build & Jalankan

### 4.1 Windows CMD (satu baris)
```cmd
docker compose -f docker\docker-compose.yml down -v && docker compose -f docker\docker-compose.yml build --no-cache && docker compose -f docker\docker-compose.yml up -d
```

### 4.2 Linux/macOS
```bash
docker compose -f docker/docker-compose.yml down -v && docker compose -f docker/docker-compose.yml build --no-cache && docker compose -f docker/docker-compose.yml up -d
```

### 4.3 Verifikasi
```cmd
docker compose -f docker\docker-compose.yml ps
curl.exe http://localhost:8001/health
curl.exe http://localhost:8001/raft/state
```

---

## 5) Cara Demo (ringkas)
Gunakan **README_demo_testing.md** untuk perintah lengkap. Contoh cepat (Windows CMD):

**Queue – seed sekali lalu consume+ACK (ID deterministik):**
```cmd
docker compose -f docker\docker-compose.yml exec redis sh -c "redis-cli DEL q:t q:inflight:t >/dev/null && redis-cli RPUSH q:t '{\"ts\":0,\"data\":{\"x\":1}}' >/dev/null && redis-cli TYPE q:t && redis-cli LLEN q:t"
```
```cmd
curl.exe -X POST http://localhost:8002/queue/consume -H "Content-Type: application/json" -d "{\"topic\":\"t\",\"consumer\":\"c1\"}"
```
```cmd
curl.exe -X POST http://localhost:8002/queue/ack -H "Content-Type: application/json" -d "{\"topic\":\"t\",\"id\":\"dad11f12fd336e4d87ebd58c6aaa2579\"}"
```

**Lock – exclusive lalu shared:**
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
curl.exe -X POST http://localhost:8001/lock/acquire -H "Content-Type: application/json" -d "{\"resource\":\"r2\",\"owner\":\"u1\",\"mode\":\"shared\"}" && curl.exe -X POST http://localhost:8002/lock/acquire -H "Content-Type: application/json" -d "{\"resource\":\"r2\",\"owner\":\"u2\",\"mode\":\"shared\"}"
```

**Cache – put → get → invalidate → get ulang:**
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

## 6) Testing

### 6.1 Pytest (Windows)
```cmd
py -3 -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt && .\.venv\Scripts\pip install pytest-asyncio && set PYTHONPATH=%CD% && set REDIS_URL=redis://localhost:6379/0 && .\.venv\Scripts\pytest -q
```

### 6.2 Locust (headless)
```cmd
.\.venv\Scripts\locust -f benchmarks\load_test_scenarios.py --headless --host http://localhost:8001 -u 50 -r 5 -t 1m
```

---

## 7) Monitoring & Metrics
- `/metrics` (Prometheus), `/health`, `/raft/state` pada tiap node

---

## 8) Scaling
- Menambah node (Linux/macOS contoh): `docker compose -f docker/docker-compose.yml up -d --scale node=5`  
  Perbarui `PEERS` atau gunakan service discovery bila dipindah ke Kubernetes.

---

## 9) Troubleshooting (ringkas)
- **ModuleNotFoundError: src** → jalankan pytest dengan `set PYTHONPATH=%CD%`
- **HTTP 500 consume** → reset `q:t` dan `q:inflight:t` lalu seed ulang
- **409 pada test lock** → hapus `locks:r1` & `locks:r1:owners` atau gunakan DB Redis lain
- **Container node exit** → rebuild image terbaru
- **PowerShell** → pakai `curl.exe` atau `Invoke-RestMethod`
- **JSON** → gunakan `"` dan escape `"`

---

## 10) Shutdown & Cleanup
```cmd
docker compose -f docker\docker-compose.yml down -v
```

Selesai.
