import numpy as np
import sys
import os
import asyncio
from collections import OrderedDict
from caproto.server import ioc_arg_parser, run, pvproperty, PVGroup
from caproto import ChannelType
import simulacrum
import zmq
from zmq.asyncio import Context
import csv 

L = simulacrum.util.SimulacrumLog(os.path.splitext(os.path.basename(__file__))[0], level='INFO')

#A service to describe a single heater. The cryo model will put together sets of heaters

class HeaterPV(PVGroup):
    power = pvproperty(value=0.0, name=':POWER', precision=1)

    def  __init__(self, change_callback, initial_values, *args, **kwargs):
       super().__init__(*args, **kwargs)
       cav_gradient = initial_values[0] #Necessary? Might only need it for the cryo model
       self.power._data['value'] = initial_values[1]
       
    @power.putter
    async def power(self, instance, value)
        await self.power.write(value)
        return   

class HeaterService(simulacrum.Service):
    def __init__(self):
        super().__init__()
        self.ctx = Context.instance()
        #cmd socket is a synchronous socket, we don't want the asyncio context.
        self.cmd_socket = zmq.Context().socket(zmq.REQ)
        self.cmd_socket.connect("tcp://127.0.0.1:{}".format(os.environ.get('MODEL_PORT', 12312)))
        init_vals = self.get_heaters_from_file()
        heater_pvs = {device_name: HeaterPV(self.on_heater_change, initial_values=init_vals[device_name], prefix=device_name) for device_name in init_vals.keys()}

    def get_heaters_from_file(self):
        init_vals = {}
        # We need to get init_vals into the form:
        # {device1: (variable1, variable2, variable3), device2: (...), ...}
        with open('cryo_heaters.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)


def main():
    device = ?? #here we need to attach a cryo model connection 

        
    
                                  
                                  
