import os
import sys
import asyncio
import numpy as np
from caproto.server import ioc_arg_parser, run, pvproperty, PVGroup
import simulacrum
import zmq
from zmq.asyncio import Context
import csv

cryomodules = ['CM01','CM02','CM03','CM04','CM05','CMO6','CM07','CM08','CM09','CM10','CM11','CM12','CM13','CM14','CM15','CM16','CM17','CM18','CM19','CM20','CM21','CM22','CM23','CM24','CM25','CM26','CM27','CM28','CM29','CM30','CM31','CM32','CM33','CM34','CM35']

#set up python logger
L = simulacrum.util.SimulacrumLog(os.path.splitext(os.path.basename(__file__))[0], level='INFO')
# valve, temp, fluid level
class cavityPV(PVGroup):
    """Instantiates the PVs"""
     #alias_name = pvproperty(value=0.0, name=':TAO_NAME') 
    # generic format for the pv extrapolated from klystron_service.py
 
class heaterPV(PVGroup):
    """Instantiates the heater PVs. 8 per cryomodule"""
    heater1 = pvproperty(value=0.0, name=':1155:HV', units='W')
    heater2 = pvproperty(value=0.0, name=':1255:HV')
    heater3 = pvproperty(value=0.0, name=':1355:HV')
    heater4 = pvproperty(value=0.0, name=':1455:HV')
    heater5 = pvproperty(value=0.0, name=':1555:HV')
    heater6 = pvproperty(value=0.0, name=':1655:HV')
    heater7 = pvproperty(value=0.0, name=':1755:HV')
    heater8 = pvproperty(value=0.0, name=':1855:HV')
    
    def __init__(self, device_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_name = device_name
        #self.heater1._data['value'] = 1


class fluidLevelPV(PVGroup):
    """Instantiates the liquid level PVs. 2 per cryomodule"""
    upstreamLVL = pvproperty(value=0.0, name=':2601:US:LVL')
    downstreamLVL = pvproperty(value=0.0, name=':2301:DS:LVL')
    print('Test')

    def __init__(self, device_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_name = device_name
        self.upstreamLVL._data['value'] = 60 # For instance, CLL:CM01:2601:US:LVL
        #print(self.upstreamLVL._data.keys())


class cryoService(simulacrum.Service):
    """A service for the cryo module. Includes
    PVs: temperature, liquid level, and valve
    control."""
    def __init__(self):
        super().__init__()
        self.ctx = Context.instance()
        self.cmd_socket = zmq.Context().socket(zmq.REQ)
        self.cmd_socket.connect("tcp://127.0.0.1:{}".format(os.environ.get('MODEL_PORT',12312)))
        #heaters, fluids, jtValves = get_cryo_devices()
        #print(fluidLevelPV('CLL:CM01', prefix='CLL
        heaters = {cm: heaterPV('CHTR:'+cm+':', prefix = 'CHTR:'+cm+':') for cm in cryomodules}
        fluids = {cm: fluidLevelPV('CLL:'+cm+':', prefix = 'CLL:'+cm+':') for cm in cryomodules} 
        self.add_pvs(heaters)
        self.add_pvs(fluids)
        for pv in self:
            print(pv)
        #print(cryoModulePVs['CM01'])
        return;

        def get_cryo_devices(self):
            heaters = [('CHTR:' + cm + ':') for cm in cryomodules]
            fluids = [('CLL:' + cm + ':') for cm in cryomodules]
            jtValves = [('CPV:' + cm + ':') for cm in cryomodules]
            return heaters, fluids, jtValves






#    def get_cryo_devices(self):
#        init_vals = {}
#        with open('cryo_devices.csv', mode='r') as file:
#            cryo_devices = csv.reader(file)
#            for line in cryo_devices:
#                print(line)
#                init_vals[line[1]] = (line[0], cryoPV.heater1, cryoPV.heater2, cryoPV.heater3, cryoPV.heater4, cryoPV.heater5, cryoPV.heater6, cryoPV.heater7, cryoPV.heater8)

    
            
        


    
def main():
    service = cryoService()
    loop = asyncio.get_event_loop()
    _, run_options = ioc_arg_parser(
        default_prefix='',
        desc="Simulated Cryo Service")
    run(service, **run_options)
    
if __name__ == '__main__':
    main()



