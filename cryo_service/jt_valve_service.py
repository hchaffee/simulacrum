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

class ValvePV(PVGroup):
    #Valve position PVs
    pos = pvproperty(value=0.0, name=':POS_RBV', precision=1) # %
    posDes = pvproperty(value=0.0, name=':POS', precision=1) # %
    posSet = pvproperty(value=0.0, name=':POS_SETPT', precision=1) # %
    mode = pvproperty(value=0.0, name=':MODE', precision=1)
    alarm = pvproperty(value=0.0, name=':ALM', precision=1) 
    #alarm:  0=position tracking alarm; 1=position greater than expected, 2=normal

    #PID Control PVs
    proportional = pvproperty(value=0.0, name=':P', precision=1)
    integral = pvproperty(value=0.0, name=':I', precision=1)
    derivative = pvproperty(value=0.0, name=':D', precision=1)
    
    #Control values (cv) PVs
    cvSet = pvproperty(value=0.0, name=':SETPT_RBV', precision=1) # %
    cv = pvproperty(value=0.0, name=':CV_VALUE', precision=1) # %
    cvMax = pvproperty(value=0.0, name=':CV_MAX', precision=1)
    cvMin = pvproperty(value=0.0, name=':CV_MIN', precision=1)
    cvMaxROC = pvproperty(value=0.0, name=':ROC', precision=1) # %/s
    loopPeriod = pvproperty(value=0.0, name=':TRG', precision=1) # s
    operatorSet = pvproperty(value=0.0, name=':SETPT', precision=1) # %
    
