
import asyncio

from bleak import BleakScanner,BleakClient
import bleak

from sp110e.driver import Driver

async def flash_device(client):
    device=Driver()
    await device.connect_with_device(client)
    await device.write_parameters({
        'ic_model': 'WS2811',
        'sequence': 'BGR',
        'pixels': 60
    })
    await device.write_parameter('state', True)
    await device.write_parameter('color', [0, 255, 0])
    await device.write_parameter('state', False)

def get_all_characteristics(client):
    uuids=[]
    for service in client.services:
        for characteristic in service.characteristics:
            uuids.append([service.uuid,characteristic.uuid])
    return uuids

CHARACTERISTIC = '0000ffe1-0000-1000-8000-00805f9b34fb'
target_service='0000ffb0-0000-1000-8000-00805f9b34fb'
already_found=set()
async def main():
    #['0000ffb0-0000-1000-8000-00805f9b34fb']
    #async with BleakScanner(service_uuids=['0000ffb0-0000-1000-8000-00805f9b34fb']) as scanner:
    async with BleakScanner() as scanner:
        n=5
        async for bd, ad in scanner.advertisement_data():
            if bd in already_found:
                continue
            if ad.local_name is None or 'SP110E' not in ad.local_name:
                continue

            already_found.add(bd)
            print(bd.address)
            continue
            #breakpoint()
            found = len(bd.name or "") > n or len(ad.local_name or "") > n
            print(f" Found{' it' if found else ''} {bd!r} with {ad!r}")
            try:
                async with BleakClient(bd) as client:
                    try:
                        await client.connect()
                    except bleak.exc.BleakError as e:
                        pass
                    print("\n\t".join(map(str,get_all_characteristics(client))))
                    await flash_device(client)
                    #await client.start_notify(CHARACTERISTIC, _callback_handler)
                    #print("FOUND A HIT",d.address)
            except TimeoutError:
                pass



if __name__ == "__main__":
    asyncio.run(main())