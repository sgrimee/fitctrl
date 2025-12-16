import asyncio
from bleak import BleakScanner


async def main():
    """Scan for BLE devices and print them."""
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    print(f"\nFound {len(devices)} device(s):\n")
    for d in devices:
        print(d)


if __name__ == "__main__":
    asyncio.run(main())
