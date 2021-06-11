#!/usr/bin/env python3
import os
import argparse
import sys
import pickle
import time
import numpy as np
import zmq
from p4p.nt import NTTable
from p4p.server import Server as PVAServer
from p4p.server.asyncio import SharedPV
from zmq.asyncio import Context
import simulacrum
# Did not import pytao...

cryo_model_dir = os.path.dirname(os.path.realpath(__file__))
L = simulacrum.util.SimulacrumLog(os.path.splitext(os.path.basename(__file__))[0], level='INFO')

class CryoModel:
    def __init__(self, init_file, name, enable_jitter=False):
        self.name = name
        self.ctx = Context.instance()
        self.model_broadcast_socket = zmp.Context().socket(zmq.PUB)
        self.model_broadcast_socket.bind("tcp://*:{}".format(os.environ.get('MODEL_BROADCAST_PORT', @@@)))
        self.loop = asyncio.get_event_loop()
        #self.jitter_enabled = enable_jitter not including for now

    def start(self):
        L.info("Starting %s Cryo Model.", self.name)
        try:
            zmq_task = self.loop.create_task(self.recv())
            broadcast_task = self.loop.create_task(self.broadcast_model_changes())
            self.loop.run_forever()
        except KeyboardInterrupt:
            L.info("Shutting down Cryo Model.")
            zmq_task.cancel()
            broadcast_task.cancel()
        finally:
            self.loop.close()
            L.info("Cryo Model shutdown complete.")

    def get_heater_devices(self):
        """Reads the csv to get the list of heater devices."""
        with open("cryo_heaters.csv", newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader[1:]:
        
