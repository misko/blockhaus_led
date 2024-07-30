"""Wait for button presses/releases and log events.
"""

from lpminimk3 import ButtonEvent, Mode, find_launchpads
import random
import sys

import asyncio
from sp110e.driver import Driver


addresses = [
    "A8:8A:1E:1A:EF:E0",
    "38:93:0E:0F:9C:74",
    "A8:8A:1E:1C:76:1A",
    "23:10:19:00:06:B1",
]
addresses = [
    "61EF3343-6CEC-C59C-D2CD-6861746676BD",
    "C836586A-EFA8-468F-E3CF-6840F1D5A7C0",
    "B6590ABB-381A-F367-CF6D-8308C083CD17",
    "8BC7564F-B8DB-E533-2401-481547665B23",
]


async def pulse_color(device):
    await device.write_parameter("state", True)
    await device.write_parameter("color", [0, 255, 0])
    await device.write_parameter("color", [255, 0, 0])
    await device.write_parameter("color", [0, 0, 255])
    await device.write_parameter("state", False)


async def led_on(device):
    await device.write_parameter("state", True)


async def led_blue(device):
    await device.write_parameter("color", [255, 0, 0])
    await asyncio.sleep(0.5)


async def led_red(device):
    await device.write_parameter("color", [0, 0, 255])
    await asyncio.sleep(0.5)


async def led_green(device):
    await device.write_parameter("color", [0, 255, 0])
    await asyncio.sleep(0.5)


async def led_off(device):
    await device.write_parameter("state", True)


color_cycle = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


def next_in_cycle(color):
    return color_cycle[(color_cycle.index(color) + 1) % len(color_cycle)]


def bgr2rgb(bgr):
    return (bgr[2], bgr[1], bgr[0])


def grb2rgb(grb):
    return (grb[1], grb[0], grb[2])


async def load_devices():
    lp.panel.reset()

    devices = []
    for adress in addresses:
        device = Driver()
        await device.connect(adress)
        devices.append(device)
        # device.print_parameters()
        await device.write_parameters(
            {"ic_model": "WS2811", "sequence": "BGR", "pixels": 60}
        )
        print("ADDED", device, len(devices))
    await asyncio.sleep(0.5)

    # (green,red,blue)
    init_color_bgr = (0, 0, 255)
    color_state = [init_color_bgr] * len(devices)
    for i in range(len(devices)):
        lp.panel.led(i, 1).color = grb2rgb(init_color_bgr)
        await devices[i].write_parameter("color", init_color_bgr)
    return {"color_state": color_state, "devices": devices}

    # for i in range(10):
    #     await asyncio.gather(*[led_on(_device) for _device in devices])
    #     await asyncio.gather(*[led_blue(_device) for _device in devices])
    #     await asyncio.gather(*[led_red(_device) for _device in devices])
    #     await asyncio.gather(*[led_green(_device) for _device in devices])
    #     await asyncio.gather(*[led_off(_device) for _device in devices])
    # # await device.write_parameters({'mode': 90, 'speed': 50})
    # await device.write_parameter('brightness', 50)
    # await device.write_parameter('white', 0)
    # await device.write_parameters({'mode': 0, 'speed': 50})
    # device.print_parameters()
    # await device.disconnect()


async def toggle(x, y, state):
    print("toggle", x, y)
    if y == 0 and x < len(state["devices"]):
        next_color = next_in_cycle(state["color_state"][x])
        state["color_state"][x] = next_color
        lp.panel.led(x, 1).color = grb2rgb(next_color)
        print("DEVICE", state["devices"][x])
        await state["devices"][x].write_parameter("color", next_color)
    else:
        print("SKIP")


async def main():
    # await asyncio.gather(led_main(), asyncio.to_thread(display_main))

    while True:
        button_event = lp.panel.buttons().poll_for_event(timeout=0.01)
        if button_event is None:
            break

    state = await load_devices()
    while True:
        button_event = lp.panel.buttons().poll_for_event()
        if button_event and button_event.type == ButtonEvent.PRESS:
            await toggle(button_event.button.x, button_event.button.y - 1, state)


if __name__ == "__main__":
    """Runs script."""
    lp = find_launchpads()[0]  # Get the first available launchpad
    lp.open()  # Open device for reading and writing on MIDI interface (by default)  # noqa

    lp.mode = Mode.PROG  # Switch to the programmer mode

    print(
        "Push any button on your Launchpad to see it light up!\n"
        "Press Ctrl+C to quit.\n"
    )
    asyncio.run(main())
