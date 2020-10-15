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

# Known bug: 
# First set up your terminal. Run model_service sc_hxr in the background
# Run this file in the background
# "caput ACCL:L1B:0220:SSA:PowerOff 1"   <-- This will reveal a bug on line 137: "await self.ssaOnOff_Act.write(0)"
# For some reason, the service won't recognize ssaOnOff_Act as a valid PV to write to (pv defined on line 39)
# This is weird because there's nothing unique about the way I define ssaOnOff_Act or its putter

#set up python logger
L = simulacrum.util.SimulacrumLog(os.path.splitext(os.path.basename(__file__))[0], level='INFO')

class CavityPV(PVGroup):
    pdes = pvproperty(value=0.0, name=':PDES', precision=1)
    pmean = pvproperty(value=0.0, name=':PMEAN', precision=1)
    phas = pvproperty(value=0.0, name=':PHASE', read_only=True, precision=1)
    ades = pvproperty(value=0.0, name=':ADES', precision=1)
    aact = pvproperty(value=0.0, name=':AACT', read_only=True, precision=1)
    amean = pvproperty(value=0.0, name=':AMEAN', read_only=True, precision=1)
    gdes = pvproperty(value=0.0, name=':GDES', precision=1)
    gact = pvproperty(value=0.0, name=':GACT', read_only=True, precision=1)
    l = pvproperty(value=1.038, name=':L', read_only=True, precision=1)
    z = pvproperty(value=0.0, name = ':Z', read_only = True, precision=1)
    ssaOn_Des = pvproperty(value=1, name=':SSA:PowerOn', dtype=ChannelType.ENUM,
                      enum_strings=("False", "True")) # ssa defaults to On = True
    ssaOff_Des = pvproperty(value=0, name=':SSA:PowerOff', dtype=ChannelType.ENUM,
                      enum_strings=("False","True")) # see above
    ssa_StatusMsg = pvproperty(value=3, name=':StatusMsg', dtype=ChannelType.ENUM, 
                      enum_strings=("Unknown","Faulted","SSA Off","SSA On","Resetting Faults...","Powering ON...","Powering Off...","Fault Reset Failed...","Power On Failed...","Power Off Failed...","Rebooting SSA...","Rebooting X-Port...")) #only using 2=off, 3=on. Defaults to on
    ssaOnOff_Act = pvproperty(value=1, name=':IS_ON', dtype=ChannelType.ENUM,
                      enum_strings=("F","T"))

    ### All these rf pvs are just here nominally. They don't impact phase, gradient, etc
    rfState_Des = pvproperty(value=1, name=':RFCTRL', dtype=ChannelType.ENUM,
                             enum_strings=("Off","On")) # 0 = off, 1 = on. Defaults to on
    rfMode_Des = pvproperty(value=4, name=':RFMODECRTL', dtype=ChannelType.ENUM,
                            enum_strings=("SELAP","SELA","SEL","SEL Raw","Pulse","Chirp")) # Defaults to pulse
    rfState_Act = pvproperty(value=1, name=':RFSTATE', dtype=ChannelType.ENUM,
                             enum_strings=("Off","On")) # Defaults to on
    rfMode_Act = pvproperty(value=4, name=':RFMODE', dtype=ChannelType.ENUM,
                            enum_strings=("SELAP","SELA","SEL","SEL Raw","Pulse","Chirp")) # Defaults to pulse
    ###
    

    def __init__(self, change_callback, initial_values, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gact._data['value'] = initial_values[0] 
        self.pmean._data['value'] = initial_values[1]  #actual as placeholder for mean
        self.phas._data['value'] = initial_values[1]
        #self.z._data['value'] = initial_values[2] # currently unused
        self.device_name = initial_values[3]
        self.elem_name = initial_values[4]
        self.l._data['value'] = initial_values[5]
        self.aact._data['value'] = initial_values[0] * initial_values[5] # gact * l = aact
        self.amean._data['value'] = initial_values[0] * initial_values[5] #actual as placeholder for mean
        # Currently, initial_values[6] is rf frequency. We don't use it right now
        self.ssaOnOff_Act = initial_values[7] 
        #self.ssaOnOff_Act._data['value'] = self.ssa_on  # currently unused
        self.change_callback = change_callback 
        
### The following "putter" commands are run asynchronously, whenever we change...
### ... the value of a variable that has a putter associated with it. 
## ___________________________
## In a putter command, we can:
## 1. Do nothing, simply type "return;" beneath the async call
## 2. Trigger a *different* putter using self.pvProp.write(desired value)  (simply updates pvProp if the putter doesnt exist)
## 3. For pvproperties that are tao attributes (gradient, phase), use self.change_callback(self, value "ATTRIBUTE")
## 4. (Rarely used) Update a different variable, pvProp, without running pvProp's putter:
    ## self.pvProp._data['value'] = desired value  
    ## self.pvProp.publish(0)   ***it's always 0, regardless of the desired value!***
## __________________________
    @phas.putter
    async def phas(self, instance, value):
        print('Setting phase to ', value)
        self.change_callback(self, value, "PHAS")
        return;
    @gact.putter
    async def gact(self, instance, value):
        print('Setting gact to ', value)
        self.change_callback(self, value, "GACT") 
        return;
    @aact.putter
    async def aact(self, instance, value):
    # For now, we are making amean = aact
        self.amean._data['value'] = value 
        await self.amean.publish(0) 
        return; 
    @ssaOnOff_Act.putter
    async def ssaOnOff_Act(self, instance, value):
        print("Trying to execute on/off putter")
        if value == 0:
            self.change_callback(self, 'F', "IS_ON")
        elif value == 1:
            self.change_callback(self, 'T', "IS_ON")
        else:
            print('Invalid value for ssa on/off')
        return


    @ades.putter 
    async def ades(self, instance, value):
        print('Setting ades to ', value)
        new_gdes = value/self.l.value 
        await self.gdes.write(new_gdes) 
        return;
    @pdes.putter
    async def pdes(self, instance, value):
        print('Setting pdes to ', value)
        await self.phas.write(value)
        return;
    @gdes.putter
    async def gdes(self, instance, value):
        print('Setting gdes to ', value)
        await self.gact.write(value) 
        new_ades = value * self.l.value  
        self.ades._data['value'] = new_ades #
        print('Setting aact to ', new_ades)
        await self.aact.write(new_ades)
        await self.ades.publish(0) #
        return;

    @ssa_StatusMsg.putter
    async def ssa_StatusMsg(self, instance, value):
        if value == 'SSA Off': # 2 = 'SSA Off':
            print("Making status = SSA Off")
            await self.phas.write(0)
            await self.gact.write(0)
            await self.ssaOnOff_Act.write(0)
        elif value == 'SSA On': # 3 = 'SSA On'
            print("Making status = SSA On")
            await self.phas.write(self.pdes.value)
            await self.gact.write(self.gdes.value)
            await self.ssaOnOff_Act.write(1)
        return;
    

    @ssaOn_Des.putter
    async def ssaOn_Des(self, instance, value):
        if value == 'False': # If On = False, then we need to make Off = True 
            '''Here, I need to use the publish format because I'm trying to avoid
            triggering ssaOff_Des.putter. This avoids the two putters infinitely 
            calling each other because .publish() does not run a secondary .putter'''
            print("Making On = False")
            self.ssaOff_Des._data['value'] = 1
            await self.ssaOff_Des.publish(0)
            await self.ssa_StatusMsg.write(2) # In ssa_Status, 2 = 'SSA Off'
        else: # If On = True, then we need to make Off = False
            print("Making On = True")
            self.ssaOff_Des._data['value'] = 0
            await self.ssaOff_Des.publish(0)
            await self.ssa_StatusMsg.write(3) # In ssa_Status, 3 = 'SSA On'
        return;

    @ssaOff_Des.putter
    async def ssaOff_Des(self, instance, value):
        if value == 'False': # If Off = False, then we need to make On = True 
            '''See comments in ssaOn_Des'''
            print("Making Off = False")
            self.ssaOn_Des._data['value'] = 1
            await self.ssaOn_Des.publish(0)
            await self.ssa_StatusMsg.write(3) # In ssa_Status, 3 = 'SSA On'
        else: # If Off = True, then we need to make On = False
            print("Making Off = True")
            self.ssaOn_Des._data['value'] = 0
            await self.ssaOn_Des.publish(0)
            await self.ssa_StatusMsg.write(2) # In ssa_Status, 2 = 'SSA Off' 
        return;
            
            
        
    

def _parse_cav_table(table):
    splits = [row.split() for row in table]
    #print(splits) # Debugging printout
    return { deviceName:
                 (float(bmadGrad), float(bmadPhas), float(Z), deviceName, elemName,  float(L), float(rfFreq), str(ssa_on))
           for  (_, elemName, _, Z, L, bmadGrad, bmadPhas, rfFreq, ssa_on, deviceName) in splits if '#' not in elemName} 
# The underscores are the elements in splits which we do not want!



class CavityService(simulacrum.Service):
    def __init__(self):
        super().__init__()
        self.ctx = Context.instance()
        #cmd socket is a synchronous socket, we don't want the asyncio context.
        self.cmd_socket = zmq.Context().socket(zmq.REQ)
        self.cmd_socket.connect("tcp://127.0.0.1:{}".format(os.environ.get('MODEL_PORT', 12312)))
        init_vals = self.get_cavity_ACTs_from_model()
        cav_pvs = {device_name: CavityPV(self.on_cavity_change, initial_values=init_vals[device_name], prefix=device_name) for device_name in init_vals.keys()}
        self.add_pvs(cav_pvs)
        print("Initialization complete.")

    def get_cavity_ACTs_from_model(self):
        init_vals = {}
        # A note on the lattice: Oddly, phase and gradient are given by phi0_err and gradient_err
        # I also include rf_frequency and is_on attributes because they might be useful later on??
        # The 'alias' attribute is the device name, e.g., 'ACCL:L3B:3070'
        self.cmd_socket.send_pyobj({"cmd": "tao", "val": "show lat -no_label_lines -attribute gradient_err -attribute phi0_err -attribute rf_frequency -attribute is_on -attribute alias lcavity::*"})
        table = self.cmd_socket.recv_pyobj()['result']
        ''' The following section adds aliases to each row'''
        index = 0
        for row in table: 
            if (row.find('ACCL:') == -1) and (row.find('TCAV:') == -1): 
                elemName = table[index].split()[1]
                table[index] = row + "  NoAliasFor|" + elemName
                index += 1
            else:
                index += 1
        ''' End of adding aliases. The "NoAlias" section was needed
        because not every element has an alias, and we need a dummy
        string in place of it so that the return statement in 
        _parse_cav_table finds the same # of elements in each row'''
        init_vals = _parse_cav_table(table)
        #print(init_vals)  # Debugging printout
        return init_vals

    def on_cavity_change(self, cavity_pv, value, parameter):
        # Warning: "value" may have to be transformed to match the units that tao expects 
        element = cavity_pv.elem_name
        if parameter == "PHAS":
            cav_attr = "phi0_err";
        elif parameter == "GACT":
            cav_attr = "gradient_err";
        elif parameter == "IS_ON":
            cav_attr = "is_on";  # the is_on value is already in 'T'/'F' format
        cmd = f'set ele {element} {cav_attr} = {value}'
        #L.info(cmd)
        self.cmd_socket.send_pyobj({"cmd": "tao", "val": cmd})            
        msg = self.cmd_socket.recv_pyobj()['result']
        #L.info(msg)
   
def main():
    service = CavityService()
    loop = asyncio.get_event_loop()
    _, run_options = ioc_arg_parser(
        default_prefix='',
        desc="Simulated CM Cavity Service")
    run(service, **run_options)
    
if __name__ == '__main__':
    main()
    



        
