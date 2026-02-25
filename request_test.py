import asyncio
import aiohttp
import time
import random
from PIL import Image

URL = "http://3.235.131.177/pixel"

img = Image.open("6.png").convert("RGB").resize((128, 128))
pixels = img.load()
WIDTH, HEIGHT = 128, 128

# Build task list
tasks = []
for x in range(WIDTH):
    for y in range(HEIGHT):
        r, g, b = pixels[x, y]
        tasks.append((x, y, "R", int(r)))
        tasks.append((x, y, "G", int(g)))
        tasks.append((x, y, "B", int(b)))

TOTAL = len(tasks)  # 786,432

success_count = 0
fail_count = 0
latencies = []


async def send_pixel(session, x, y, channel, value):
    global success_count, fail_count
    t = time.time()
    try:
        async with session.post(URL, json={"x": x, "y": y, "channel": channel, "value": value}) as resp:
            latencies.append(time.time() - t)
            if resp.status == 200:
                success_count += 1
            else:
                fail_count += 1
    except Exception:
        fail_count += 1


async def run_test(target_rps):
    global success_count, fail_count
    success_count = 0
    fail_count = 0
    latencies.clear()

    print(f"\n🔥 Target: {target_rps} req/s | Total: {TOTAL} requests")

    interval = 1.0 / target_rps  # khoảng cách giữa 2 lần gửi

    connector = aiohttp.TCPConnector(limit=0)  # không giới hạn connections
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        start = time.time()
        pending = []

        for task in tasks:
            x, y, ch, val = task
            # Tạo task và gửi NGAY, không chờ response
            t = asyncio.create_task(send_pixel(session, x, y, ch, val))
            pending.append(t)

            # Giữ đúng tốc độ target_rps
            await asyncio.sleep(interval)

        # Chờ tất cả responses về
        await asyncio.gather(*pending)

        duration = time.time() - start

    actual_rps = TOTAL / duration
    avg_lat = sum(latencies) / len(latencies) * 1000 if latencies else 0
    p99_lat = sorted(latencies)[int(len(latencies) * 0.99)] * 1000 if latencies else 0

    print(f"✅ Success : {success_count}/{TOTAL}")
    print(f"❌ Failed  : {fail_count}/{TOTAL}")
    print(f"⏱  Time    : {duration:.2f}s")
    print(f"📈 Actual  : {actual_rps:.0f} req/s")
    print(f"📊 Avg lat : {avg_lat:.2f}ms")
    print(f"📊 P99 lat : {p99_lat:.2f}ms")


for target in [3000]:
    asyncio.run(run_test(target_rps=target))
    time.sleep(3)  # nghỉ giữa các level