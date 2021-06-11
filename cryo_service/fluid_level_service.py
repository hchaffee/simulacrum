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

L = simulacrum.util.SimulacrumLog(os.path.splitext(os.path.basename(__file__))[0], level='INFO')

class FluidPV(PVGroup):
    upstream = pvproperty(value=90.0, name=':US:LVL', precision=1)
    downstream = pvproperty(value=60.0, name=':DS:LVL', precision=1)

    def  __init__(self, change_callback, initial_values, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.upstream._data['value'] = initial_values[0]
        self.downstream._data['value'] = initial_values[1]

class FluidService(simulacrum.Service):
    def __init__(self):
        super().__init__()
        self.ctx = Context.instance()
        #cmd socket is a synchronous socket, we don't want the asyncio context.
        self.cmd_socket = zmq.Context().socket(zmq.REQ)
        self.cmd_socket.connect("tcp://127.0.0.1:{}".format(os.environ.get('MODEL_PORT', 12312)))
        init_vals = self.get_fluids_from_file()
        fluid_pvs = {device_name: FluidPV(self.on_fluid_change, initial_values=init_vals[device_name], prefix=device_name) for device_name in init_vals.keys()}

    def get_fluids_from_file(self):
        init_vals = {}
        # We need to get init_vals into the form:
        # {device1: (variable1, variable2, variable3), device2: (...), ...}        
                                                          
    
