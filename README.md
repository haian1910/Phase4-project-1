# Pixel Endpoint Deployment on AWS (Dual EC2 Setup)

## Overview

This project deploys a **single public `/pixel` endpoint** on AWS using two EC2 instances:

- `c5.xlarge` (4 vCPU)
- `t2.xlarge` (4 vCPU)

The system is designed to handle increasing throughput (100 req/s → 1000+ req/s) using:

- FastAPI (application layer)
- Gunicorn + Uvicorn workers (multi-process scaling)
- Nginx (reverse proxy + load balancer)

---

## Architecture

```
Client
   ↓
Nginx (running on c5.xlarge)
   ↓
FastAPI Application
   ├── c5.xlarge:8000
   └── t2.xlarge:8000
```

Only **ONE public endpoint** is exposed:

```
POST /pixel
```

Port 8000 is NOT public.  
Only port 80 (Nginx) is public.

---

## Endpoint Specification

### Request Body

```json
{
  "x": 10,
  "y": 20,
  "channel": "R",
  "value": 255
}
```

### Validation Rules

- `channel` must be `"R"`, `"G"`, or `"B"`
- `value` must be between `0` and `255`

### Example Response

```json
{
  "status": "ok",
  "received": {
    "x": 10,
    "y": 20,
    "channel": "R",
    "value": 255
  }
}
```

---

# Server Setup (Both EC2 Instances)

## 1. Connect via SSH

```bash
ssh ubuntu@<EC2-IP>
```

## 2. Update System

```bash
sudo apt update
sudo apt upgrade -y
```

## 3. Install Python

```bash
sudo apt install python3-pip python3-venv -y
```

## 4. Create Project

```bash
mkdir pixel_project
cd pixel_project
python3 -m venv venv
source venv/bin/activate
```

## 5. Install Dependencies

```bash
pip install fastapi uvicorn gunicorn
```

---

# Application Code

Create `main.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

class PixelRequest(BaseModel):
    x: int
    y: int
    channel: Literal["R", "G", "B"]
    value: int

@app.post("/pixel")
def receive_pixel(data: PixelRequest):
    if not (0 <= data.value <= 255):
        return {"error": "value must be between 0 and 255"}

    return {
        "status": "ok",
        "received": data
    }
```

---

# Run in Production Mode

Use Gunicorn with multiple workers.

On BOTH instances:

```bash
gunicorn -k uvicorn.workers.UvicornWorker main:app -w 4 -b 0.0.0.0:8000
```

Worker rule:

```
workers ≈ number of CPU cores
```

Each instance has 4 vCPU → start with 4 workers.

---

# Nginx Load Balancer (Only on c5.xlarge)

## Install Nginx

```bash
sudo apt install nginx -y
```

## Configure

Edit:

```bash
sudo nano /etc/nginx/sites-available/default
```

Replace content:

```nginx
upstream pixel_servers {
    server <PRIVATE-IP-c5>:8000;
    server <PRIVATE-IP-t2>:8000;

    keepalive 64;
}

server {
    listen 80;

    location / {
        proxy_pass http://pixel_servers;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Restart:

```bash
sudo systemctl restart nginx
```

Public endpoint:

```
http://<c5-public-ip>/pixel
```

---

# AWS Security Group Configuration

## c5.xlarge (Load Balancer)

Allow:
- HTTP (80) → 0.0.0.0/0

## Both Instances

Allow:
- TCP 8000 → only from private VPC (NOT 0.0.0.0/0)

Important:
- Do NOT expose port 8000 publicly.
- Clients must access only through Nginx.

---

# Load Testing

## Create test payload

`data.json`

```json
{"x":1,"y":2,"channel":"R","value":100}
```

## Apache Benchmark

```bash
ab -n 10000 -c 100 -p data.json -T application/json http://<PUBLIC-IP>/pixel
```

## WRK (Higher Load)

```bash
wrk -t12 -c1000 -d30s -s post.lua http://<PUBLIC-IP>/pixel
```

---

# Scaling Strategy

To support higher throughput:

1. Increase Gunicorn workers
2. Tune Nginx keepalive
3. Increase file descriptor limit:
   ```bash
   ulimit -n
   ```
4. Monitor:
   ```bash
   htop
   ss -s
   ```

If first load test succeeds but second fails:
- Likely TCP TIME_WAIT exhaustion
- Or connection limits reached

Wait 30–60 seconds between heavy tests.

---

# Performance Notes

Total bandwidth depends on response size.

Example:

If response ≈ 100 KB  
At 1000 req/s → 100 MB/s (~800 Mbps)

If response ≈ 10 KB  
At 1000 req/s → 10 MB/s (~80 Mbps)

Network capacity must match payload size.

---

# Production Safety

- Only `/pixel` is public
- No additional endpoints exposed
- Port 8000 is private
- Always test through port 80 (Nginx)
- Use keepalive to prevent connection exhaustion

---

# Final Result

✔ Single public endpoint  
✔ Load-balanced across 2 EC2 instances  
✔ Production-ready configuration  
✔ Scalable to high throughput  
✔ Secure backend isolation  
