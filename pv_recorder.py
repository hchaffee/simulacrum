import os
import epics
import csv
import time
import sys
import numpy as np
import pandas as pd
import zmq



class PVRecorder:
    def __init__(self, read_map_file):
        """ PVRecorder records PVs!  When you initialize it, it connects to
        every PV in the csv file. """
        self.read_map = []
        with open(read_map_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                pv = epics.PV("{dev}:{attr}".format(dev=row['device_name'], attr=row['attribute']))
                self.read_map.append(([], [], pv))
    
    def read_pvs(self):
        """ Record new values for all the PVs in the CSV file. """
        start = time.time()
        for data, timestamps, pv in self.read_map:
            if not pv.connected:
               # print("Could not connect to {}".format(pv.pvname))
                continue
            val = pv.get_with_metadata()
            data.append(val['value'])
            timestamps.append(val['timestamp'])
        finish = time.time()
        print("Reading PVs took {} seconds.".format(finish-start))
            
    def dataframe(self):
        """ Returns a time-aligned pandas dataframe with all of the recorded data. """
        # First, create a bunch of individual time series, one for each PV.
        series = [pd.Series(data=data, index=pd.to_datetime(timestamps, unit="s"), name=pv.pvname) for data, timestamps, pv in self.read_map]
        # Next, merge all the time series (serieses?) into one dataframe.
        all_data = series[0].to_frame().join(series[1:], how='outer')
        # Now, fill in all empty places with the last known good value.
        all_data.fillna(method="ffill", inplace=True)
        # Also backfill with the first known good value.
        all_data.fillna(method="bfill", inplace=True)
        return all_data
        
if __name__=='__main__':
    """
    This is what actually runs when you run this script.
    It instantiates a new PVRecorder, then collects data for a while.
    It also sends a Tao command to the simulacrum model service
    to create a fault at some point in time.  When the script is complete,
    it saves the pandas dataframe in an HDF5-formatted file.
    """
    print(sys.argv)
    r = PVRecorder(sys.argv[1])
    total_time = 30 #seconds
    elapsed_time = 0
    fault_time = 10 #A fault will occur this many seconds after T=0
    cmd_socket = zmq.Context().socket(zmq.REQ)
    cmd_socket.connect("tcp://127.0.0.1:{}".format(os.environ.get('MODEL_PORT', "12312")))
    fault_generated = False
##
    my_pv = epics.PV("BPMS:LI24:801:X")
    print(my_pv)
##
    print(f"Beginning recording. {total_time} remaining.")
    start_time = time.time()
    while elapsed_time < total_time:
        r.read_pvs()
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
        if not fault_generated and elapsed_time > fault_time:
            # Generate a sudden phase shift in a subbooster phase
            print(f"Causing fault at timestamp {time.time()}")
            commands = [f"set ele O_K23_{i} phase_deg_err = 5" for i in range(1,9)]
            cmd_socket.send_pyobj({"cmd": "tao_batch", "val": commands})
            result = cmd_socket.recv_pyobj()
            fault_generated = True
    print("Finished recording.  Writing file.")
    r.dataframe().to_hdf(sys.argv[2], key='df', mode='w')
    print(f"Done!  File saved as {sys.argv[2]}")
