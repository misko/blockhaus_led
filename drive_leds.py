import asyncio
from sp110e.driver import Driver


addresses=['A8:8A:1E:1A:EF:E0','38:93:0E:0F:9C:74','A8:8A:1E:1C:76:1A','23:10:19:00:06:B1']



async def pulse_color(device):
    await device.write_parameter('state', True)
    await device.write_parameter('color', [0, 255, 0])
    await device.write_parameter('color', [255, 0, 0])
    await device.write_parameter('color', [0, 0, 255])
    await device.write_parameter('state', False)

async def led_on(device):
    await device.write_parameter('state', True)

async def led_blue(device):
    await device.write_parameter('color', [255, 0, 0])
async def led_red(device):
    await device.write_parameter('color', [0, 0, 255])
async def led_green(device):
    await device.write_parameter('color', [0, 255, 0])

async def led_off(device):
    await device.write_parameter('state', True)

async def main():
    devices=[]
    for adress in addresses:
        device = Driver()
        await device.connect(adress)
        devices.append(device)
        device.print_parameters()
        await device.write_parameters({
            'ic_model': 'WS2811',
            'sequence': 'BGR',
            'pixels': 60
        })

    for i in range(10):
        await asyncio.gather(*[led_on(_device) for _device in devices])
        await asyncio.gather(*[led_blue(_device) for _device in devices])
        await asyncio.gather(*[led_red(_device) for _device in devices])
        await asyncio.gather(*[led_green(_device) for _device in devices])
        await asyncio.gather(*[led_off(_device) for _device in devices])
    #await device.write_parameters({'mode': 90, 'speed': 50})
    # await device.write_parameter('brightness', 50)
    # await device.write_parameter('white', 0)
    # await device.write_parameters({'mode': 0, 'speed': 50})
    # device.print_parameters()
    # await device.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
