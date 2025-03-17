import asyncio
from bleak import discover

async def scan_devices():
    devices = await discover()
    for d in devices:
        print(f"Name: {d.name} | Address: {d.address}")

asyncio.run(scan_devices())