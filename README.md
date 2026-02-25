# Pixel Endpoint

## Overview

This project deploys a **single public `/pixel` endpoint** on AWS using two EC2 instances:

- `c5.xlarge` (4 vCPU)
- `t2.xlarge` (4 vCPU)

The system is designed to handle increasing throughput (100 req/s → 1000+ req/s) using:

- FastAPI (application layer)
- Gunicorn + Uvicorn workers (multi-process scaling)
- Nginx (reverse proxy + load balancer)


## Architecture

```
Client
   ↓
Nginx (running on c5.xlarge)
   ↓
FastAPI Application
   ├── c5.xlarge:8000 --> Redis (running on c5.xlarge)
   └── t2.xlarge:8000 --> Redis
```

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


# Server Setup

## 1. Create Project

```bash
mkdir pixel_project
cd pixel_project
python3 -m venv venv
source venv/bin/activate
```

## 2. Install Dependencies

```bash
pip install fastapi uvicorn gunicorn
```

# Run

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
    server <PRIVATE-IP-c5>:8000 weight=x;
    server <PRIVATE-IP-t2>:8000 weight=y;

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