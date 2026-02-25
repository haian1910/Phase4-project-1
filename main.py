from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal
import redis
from PIL import Image

app = FastAPI()

# Redis connection
REDIS_HOST = "172.31.15.56"
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)


# =============================
# Request Models
# =============================

class PixelRequest(BaseModel):
    x: int
    y: int
    channel: Literal["R", "G", "B"]
    value: int


class BuildRequest(BaseModel):
    width: int
    height: int


# =============================
# Receive Pixel
# =============================

@app.post("/pixel")
def receive_pixel(data: PixelRequest):
    if not (0 <= data.value <= 255):
        return {"error": "Invalid value (0-255 only)"}

    key = f"{data.x}:{data.y}"
    r.hset(key, data.channel, data.value)

    return {"status": "ok"}


# =============================
# Refresh Redis (Clear all)
# =============================

@app.post("/refresh",include_in_schema=False)
def refresh_redis():
    r.flushdb()
    return {"status": "redis cleared"}


# =============================
# Build Image
# =============================

@app.post("/build",include_in_schema=False)
def build_image(data: BuildRequest):

    WIDTH = data.width
    HEIGHT = data.height

    img = Image.new("RGB", (WIDTH, HEIGHT))

    for key in r.keys("*"):
        try:
            x, y = map(int, key.split(":"))
        except:
            continue

        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            pixel = r.hgetall(key)

            r_val = int(pixel.get("R", 0))
            g_val = int(pixel.get("G", 0))
            b_val = int(pixel.get("B", 0))

            img.putpixel((x, y), (r_val, g_val, b_val))

    img.save("output.png")

    return {
        "status": "image built",
        "width": WIDTH,
        "height": HEIGHT
    }