"""Wait for button presses/releases and log events.
"""

import argparse
import time
from lpminimk3 import ButtonEvent, Mode, find_launchpads
import random
import sys
import bleak
import asyncio
from sp110e.driver import Driver
from sp110e.controller import Controller


# addresses = [
#     "A8:8A:1E:1A:EF:E0",
#     "38:93:0E:0F:9C:74",
#     "A8:8A:1E:1C:76:1A",
#     "23:10:19:00:06:B1",
# ]
# addresses = [
#     "61EF3343-6CEC-C59C-D2CD-6861746676BD",
#     "C836586A-EFA8-468F-E3CF-6840F1D5A7C0",
#     "B6590ABB-381A-F367-CF6D-8308C083CD17",
#     "8BC7564F-B8DB-E533-2401-481547665B23",
# ]

import pickle


class FailableDriver(Driver):
    def __init__(self,default_params):
        super().__init__()
        self.params=default_params.copy()

    async def connect(self,address,timeout=3):
        self.address=address
        try:
            await super().connect(address,timeout=timeout,auto_read=False)
        except bleak.exc.BleakError as e:
            print("Failed to connect",self.address)

    async def _write_parameter(self,*args,**kwargs):
        param,value=args
        self.params[param]=value
        try:
            if self.is_connected():
                await super()._write_parameter(*args,**kwargs)
        except:
            print("Failed to write param",self.address)
                                   
    async def read_parameters(self):
        try:
            await super().read_parameters()
        except:
            print("Failed to read param",self.address)

DEFAULT_PARAMS={'brightness':128,'speed':10,'mode':50,'state':False} 
# for a single hardware controller lookup these addresses
class MultiController:
    def __init__(self,addresses):
        self.addresses=sorted(list(addresses))
        self.async_controllers={}
        self.all_controllers=set()
        for address in self.addresses:
            controller=FailableDriver(DEFAULT_PARAMS) #address) #, timeout=2, retries=2**32)
            self.async_controllers[address]=controller
            self.all_controllers.add(controller)
        #TODO this needs to be params per controller not here

    async def connect(self):
        for controller_name,controller in self.async_controllers.items():
            print("Connecting to",controller_name)
            await controller.connect(controller_name)
        # for some reason params are all 0s?
        #await self.check_params(checks_before_return=-1)

    async def check_params(self, checks_before_return=1):
        controller_names=list(self.async_controllers.keys())
        random.shuffle(controller_names)
        #check brightness and mode
        for controller_name in controller_names:
            #print("CHECKING",controller_name)
            controller=self.async_controllers[controller_name]
            if controller.is_connected():
                for param_name,param_value in controller.params.items():
                    if controller._parameters[param_name]!=param_value:
                        print("Fixing",controller_name,param_name)
                        await controller._write_parameter(param_name,param_value)
                        checks_before_return-=1
                        if checks_before_return==0:
                            return
        
        for controller_name in controller_names:
            controller=self.async_controllers[controller_name]
            await controller.read_parameters()
            print(controller._parameters)
                        

    async def check_connect(self, checks_before_return=1):
        #TODO randomize the controller names so if we have one broken one 
        controller_names=list(self.async_controllers.keys())
        random.shuffle(controller_names)
        #check connection
        for controller_name in controller_names:
            controller=self.async_controllers[controller_name]
            if not controller.is_connected():
                print("Connecting to",controller_name)
                await controller.connect(controller_name,timeout=0.5)
                checks_before_return-=1
                if checks_before_return==0:
                    return
        return
    
    async def check_connect_and_params(self,checks_before_return):
        self.check_connect(checks_before_return=checks_before_return)
        self.check_params(checks_before_return=checks_before_return)

    def controllers_in_addresses(self,addresses):
        if addresses is None:
            return self.all_controllers
        l=set()
        for controller in self.all_controllers:
            if controller.address in addresses:
                l.add(controller)
        return l
    
    async def switch_on(self,addresses=None):
        #self.params['state']=True
        await asyncio.gather(*[controller._write_parameter("state",True) for controller in self.controllers_in_addresses(addresses)])
        await self.check_connect()
        await asyncio.gather(*[controller.read_parameters() for controller in self.controllers_in_addresses(addresses)])
    
    async def switch_off(self,addresses=None):
        #self.params['state']=False
        await asyncio.gather(*[controller._write_parameter("state",False) for controller in self.controllers_in_addresses(addresses)])
        await self.check_connect()
        await asyncio.gather(*[controller.read_parameters() for controller in self.controllers_in_addresses(addresses)])
    
    async def set_mode(self,mode,addresses=None):
        #self.params['mode']=mode
        await asyncio.gather(*[controller._write_parameter("mode",mode) for controller in self.controllers_in_addresses(addresses)])
        await self.check_connect()
        await asyncio.gather(*[controller.read_parameters() for controller in self.controllers_in_addresses(addresses)])
    

#class View(self,)

class Model:
    def __init__(self,pkl_fns,map_fn,queue):
        self.queue=queue
        #TODO find the best RSSI per controller
        self.address_to_controller={}
        self.controller_to_addresses={}
        assert(len(pkl_fns)==1)
        controller_name=pkl_fns[0].split('_')[1].split('.')[0]
        
        print("Controller",controller_name)
        for address in pickle.load(open(pkl_fns[0],'rb')):
            self.address_to_controller[address]=controller_name
            if controller_name not in self.controller_to_addresses:
                self.controller_to_addresses[controller_name]=set()
            self.controller_to_addresses[controller_name].add(address)

        self.multicontrollers={}
        for controller in self.controller_to_addresses:
            self.multicontrollers[controller]=MultiController(self.controller_to_addresses[controller])
        
        self.current_button_handler=None
        self.current_page=None

        self.sides={'setup':[],'front':[],'back':[],'left':[],'right':[]}
        #self.sides_mode={'setup':10,'front':10,'back':10,'left':10,'right':10}


    async def switch_side(self,side):
        self.current_button_handler=self.render_side_button_handler
        self.current_page={'page':'render_side','side':side}
        self.render_side()

    def render_side(self):
        self.lp.panel.reset() # turn off all leds
        button_idx=-1
        if 'selected' in self.current_page:
            button_idx=self.current_page['selected']
        for idx in range(len(self.sides[self.current_page['side']])):
            if idx==button_idx:
                self.lp.panel.led(idx,1).color = (255,255,255)
            else:
                self.lp.panel.led(idx,1).color = (0,0,255)
        pass

    def button_name_rewrite(self,name):
        if name=='session':
            return 'setup'
        elif name=='up':
            return 'front'
        elif name=='down':
            return 'back'
        return name
    
    def button_to_idx(self,button):
        return button.x+(button.y-1)*8

    async def render_side_button_handler(self,button,start_time,deltatime):
        if deltatime>0.0:
            #print(button)
            if hasattr(button,'x'):
                #print(button)
                pass
            return button,start_time# this is a hold
        print("RPESS ",button,deltatime)
        name=self.button_name_rewrite(button.name)
        if name=='scene_launch_1':
            #cycle through colors
            new_mode=random.randint(0,255) % 30
            for controller in self.multicontrollers:
                await self.multicontrollers[controller].set_mode(new_mode,addresses=self.sides[self.current_page['side']])
            pass
        elif name in ['front','back','right','left','setup']:
            if 'selected' in self.current_page:
                #move 
                controller=self.sides[self.current_page['side']][self.current_page['selected']]
                self.sides[name].append(controller)
                self.sides[self.current_page['side']].remove(controller)
                self.current_page.pop('selected')
                self.render_side()
            else:
                await self.switch_side(name)
        elif hasattr(button,'x'):
            #this is a grid button
            button_idx=self.button_to_idx(button)
            print("BUTTON IDX",button_idx,len(self.sides[self.current_page['side']]))
            if button_idx<=len(self.sides[self.current_page['side']]):
                self.current_page['selected']=button_idx
            self.render_side()
        else:
            print("MISSIN",name)
        
    async def press(self,button,start_time,deltatime):
        if self.current_button_handler is None:
            return None
        return await self.current_button_handler(button,start_time,deltatime)

    async def run(self):
        self.lp = find_launchpads()[0]  # Get the first available launchpad
        self.lp.open()  # Open device for reading and writing on MIDI interface (by default)  # noqa

        self.lp.mode = Mode.PROG  # Switch to the programmer mode

        #flush all existing presses
        while True:
            button_event = self.lp.panel.buttons().poll_for_event(timeout=0.01)
            if button_event is None:
                break

        #first connect to everything
        for controller in self.multicontrollers:
            await self.multicontrollers[controller].connect()

        #TODO load saved config
        for controller in self.multicontrollers:
            self.sides['setup']+=self.controller_to_addresses[controller]



        await self.switch_side('setup')
        #wait for button press
        current_press=None
        while True:
            #print("wait")
            button_event = await asyncio.to_thread(self.lp.panel.buttons().poll_for_event,timeout=20.0) #() #timeout=0.01)
            if button_event is not None:# and button_event.type == ButtonEvent.PRESS:
                #print(button_event)
                #breakpoint()
                if button_event.type == ButtonEvent.PRESS:
                    await self.press(button_event.button,time.time(),0.0)
                    current_press=(button_event.button,time.time())
                elif current_press is not None and button_event.type == ButtonEvent.RELEASE:
                    await self.press(current_press[0],current_press[1],button_event.deltatime)
                    current_press=None
                print("BUTTON",button_event)
            else:
                if current_press is not None:
                    current_press=await self.press(current_press[0],current_press[1],time.time()-current_press[1])
                #if we are sitting idle might as well try to connect
                await self.multicontrollers[controller].check_connect()
            #await asyncio.sleep(0.1)
        return
        await self.multicontrollers['hci0'].switch_on()
        await self.multicontrollers['hci0'].set_mode(10)
        print("1")
        await self.multicontrollers['hci0'].check_params(-1)
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].set_mode(3)
        await self.multicontrollers['hci0'].check_params(-1)
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].set_mode(20)
        await self.multicontrollers['hci0'].check_params(-1)
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].set_mode(5)
        await self.multicontrollers['hci0'].check_params()
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].switch_off()
        return

    async def run_old(self):
        for controller in self.multicontrollers:
            await self.multicontrollers[controller].connect()
        await self.multicontrollers['hci0'].switch_on()
        await self.multicontrollers['hci0'].set_mode(10)
        print("1")
        await self.multicontrollers['hci0'].check_params(-1)
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].set_mode(3)
        await self.multicontrollers['hci0'].check_params(-1)
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].set_mode(20)
        await self.multicontrollers['hci0'].check_params(-1)
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].set_mode(5)
        await self.multicontrollers['hci0'].check_params()
        await asyncio.sleep(5)
        print("1")
        await self.multicontrollers['hci0'].switch_off()
        return



def bgr2rgb(bgr):
    return (bgr[2], bgr[1], bgr[0])


def grb2rgb(grb):
    return (grb[1], grb[0], grb[2])

def button_press_to_queue(queue):
    #start listenin for real presses   
    pass

# async def main_old():
#     # await asyncio.gather(led_main(), asyncio.to_thread(display_main))


#     state = await load_devices()
#     while True: 
#         button_event = lp.panel.buttons().poll_for_event()
#         if button_event and button_event.type == ButtonEvent.PRESS:
#             await toggle(button_event.button.x, button_event.button.y - 1, state)

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p','--pkls', nargs='+', help='pkls', required=True)
    return parser

async def main(args):
    queue = asyncio.Queue()
    m=Model(pkl_fns=args.pkls,map_fn='map.out',queue=queue)

    
    # task1 = asyncio.create_task(
    #     )
    task2 = asyncio.create_task(
        m.run())
    task1= asyncio.create_task(asyncio.to_thread(button_press_to_queue,queue))
    await task1
    await task2
    #await task1
    #await task1
    #await task2

if __name__ == "__main__":

    parser = get_parser()
    args = parser.parse_args()
    asyncio.run(main(args))
    sys.exit()
    
