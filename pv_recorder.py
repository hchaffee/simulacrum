import os
import epics
import csv
import time
import sys
import numpy as np
import pandas as pd
import zmq
import random



#Things to have running via the fastx window:
# mcc-simul
# model service cu_hxr
# bpm service
# bmag service 
# env
# python3 pv_recorder.py fault_data_cu_hxr.csv 

class PVRecorder:
    def __init__(self, read_map_file):
        """ PVRecorder records PVs!  When you initialize it, it connects to
        every PV in the csv file. """
        self.read_map = []
        with open(read_map_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['device_name'] == 'BPMS:UNDH:1305':
                    pv = epics.PV("BPMS:LTUH:990:{attr}".format(dev="BPMS:LTUH:990", attr=row['attribute']))
                    pass
                else:
                    pv = epics.PV("{dev}:{attr}".format(dev=row['device_name'], attr=row['attribute']))
                    self.read_map.append(([], [], pv))
    
    def read_pvs(self):
        """ Record new values for all the PVs in the CSV file. """
        start = time.time()
        time.sleep(5)
        for data, timestamps, pv in self.read_map:
            if not pv.connected:
                #print("Could not connect to {}".format(pv.pvname))
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
    r = PVRecorder(sys.argv[1])
    total_time = 30 #seconds
    elapsed_time = 0
    fault_time = 10 #A fault will occur this many seconds after T=0
    cmd_socket = zmq.Context().socket(zmq.REQ)
    cmd_socket.connect("tcp://127.0.0.1:{}".format(os.environ.get('MODEL_PORT', "12312")))
    fault_generated = False
    print(f"Beginning recording. {total_time} remaining.")
    start_time = time.time()
    while elapsed_time < total_time:
        r.read_pvs()
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
        if not fault_generated and elapsed_time > fault_time:
            # Generate a sudden phase shift in a subbooster phase
            #print(f"Causing fault at timestamp {time.time()}")
            #Randomize the error parameters: sector, station, phase error

            # Sector & stations come from oracle
            sector = 23 #random.randrange(22, 27) # the klystron sector
            error = random.randrange(10, 40)  # the error in klystron phase
            station = 1
            #if sector == 21:   #sector 21 is missing a station 2
            #    station = random.choice([1, 3, 4, 5, 6, 7, 8])
            #elif sector == 24: #sector 24 is missing stations 7, 8
            #    station = random.choice([1, 2, 3, 4, 5, 6])
            #else:              # all other sectors have stations 1 thru 8 inclusive
            #    station = random.randrange(1,9)
            print("Sector: ",sector,", Station: ",station,", Error: ",error)
            commands = [f"set ele O_K{sector}_{station} phase_deg_err = {error}"]
            cmd_socket.send_pyobj({"cmd": "tao_batch", "val": commands})
            result = cmd_socket.recv_pyobj()
            fault_generated = True
    print("Finished recording.  Writing file.")
    filename = f"sector{sector}_station{station}_err{error}.csv"
    r.dataframe().to_csv(filename)
    #r.dataframe().to_hdf(filename, key='df', mode='w')
    print(f"Done!  File saved as {filename}")
    
#### comment out the next 5 lines if all stations need to be reset
    print("Resetting the fault...")
    reset_commands = [f"set ele O_K{sector}_{station} phase_deg_err = 0"]
    cmd_socket.send_pyobj({"cmd": "tao_batch", "val": reset_commands})
    reset_result = cmd_socket.recv_pyobj()  
    quit()
#### 

#### The rest of this code resets all klystron phase errors back to 0, if needed
    print("Now we need to reset the errors in our system...")
    for sectors in (21,22,23,24,25,26,27,28,29,30):
        if sectors == 21:   #sector 21 is missing a station 2
            stations = [1, 3, 4, 5, 6, 7, 8]
        elif sectors == 24: #sector 24 is missing stations 7, 8
            stations = [1, 2, 3, 4, 5, 6]
        else:              # all other sectors have stations 1 thru 8 inclusive
            stations = [1,2,3,4,5,6,7,8]
    
        reset_commands = [f"set ele O_K{sectors}_{i} phase_deg_err = 0" for i in stations]
        cmd_socket.send_pyobj({"cmd": "tao_batch", "val": reset_commands})
        reset_result = cmd_socket.recv_pyobj()
    print("All sectors done resetting")
    quit()
