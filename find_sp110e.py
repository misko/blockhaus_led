
import argparse
import asyncio
import time
from bleak import BleakScanner,BleakClient
import bleak
import pickle

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

def sp110e_filter(bd , adv) -> bool:
    if adv.local_name is not None and 'sp110' in adv.local_name.lower():
        return True
    return False

CHARACTERISTIC = '0000ffe1-0000-1000-8000-00805f9b34fb'
target_service='0000ffb0-0000-1000-8000-00805f9b34fb'
already_found={}
async def main(args):
    #['0000ffb0-0000-1000-8000-00805f9b34fb']
    #async with BleakScanner(service_uuids=['0000ffb0-0000-1000-8000-00805f9b34fb']) as scanner:
    async with BleakScanner(adapter=args.adapter) as scanner:
        start_time=time.time()
        #print("WTF")
        async for bd, ad in scanner.advertisement_data():
            if time.time()-start_time>args.time:
                return
            #print("CONSIDER BD",bd,ad)
            if ad.local_name is None: # wait until we get name
                continue
            #if bd in already_found:
            #    continue
            if ad.local_name is None or 'SP110E' not in ad.local_name:
                continue

            #already_found.add(bd)
            if bd.address not in already_found:
                already_found[bd.address]=ad.rssi
            else:
                alpha=0.99
                already_found[bd.address]*=0.99
                already_found[bd.address]+=bd.rssi*(1.0-alpha)
            #print(bd.address,ad.rssi)
            print(already_found)
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


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--adapter",
        type=str,
        required=True
    )
    parser.add_argument(
        "--time",
        type=int,
        default=10
    )
    return parser

if __name__ == "__main__":

    parser = get_parser()
    args = parser.parse_args()
    asyncio.run(main(args))
    pickle.dump(already_found, open(f"sp110e_{args.adapter}.pkl",'wb'))