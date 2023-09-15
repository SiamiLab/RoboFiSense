import socket
import signal
import sys
import time 
import pickle
from datetime import datetime
from PyQt6.QtCore import QThread, QTimer, QCoreApplication, QObject, pyqtSignal
import numpy as np
import argparse
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("--frequency", type=int, help="frequency to store CSI data", required=True)
parser.add_argument("--packetnum", type=int, help="number of packets to receive", required=True)
args = parser.parse_args()

frequency = args.frequency
num_of_packets_to_collect = args.packetnum


class ThreadCSI(QThread):
    process_started = pyqtSignal()
    def __init__(self) -> None:
        super().__init__()
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.bind(("", 5500))
        
        self.last_packets = {} # key: ip addr, value: (time, data)
        self.collector = {}
        self.first_time = True
        self.run_flag = True
                    
    def run(self) -> None:
        while True:
            if not self.run_flag:
                continue
            data, addr = self.client.recvfrom(4096)
            self.last_packets[addr[0]] = (time.time_ns(), data)
            if self.first_time:
                print("don't worry I'm receiving some stuff")
                subprocess.Popen('say RECEIVING', shell=True)
                self.first_time = False
                self.process_started.emit()
    
    def handle_timer(self):
        if not self.run_flag:
            return
        for key, value in self.last_packets.items(): # key: ip addr, value: (time, data)
            if not key in self.collector.keys():
                self.collector[key] = {}
            if len(self.collector[key].keys()) < num_of_packets_to_collect:
                self.collector[key][value[0]] = value[1]
        if np.all(np.array([len(self.collector[key].keys()) for key in self.collector.keys()]) >= num_of_packets_to_collect) and len(self.collector.keys()) != 0:
            self.ctrl_c(reset_=True)
            
    def ctrl_c(self, reset_=False):
        self.run_flag = False
        print('\nnumber of collectors: ' + str(len(self.collector)))
        for key in self.collector.keys():
            print(f' - number of samples from {key} is: ' + str(len(self.collector[key])))
        
        print('Writing data to file. please wait!')
        filename = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")+'_csi.dat'
        pickle_out = open(filename,"wb")
        pickle.dump(self.collector, pickle_out)
        pickle_out.close()
        print("Done. Saved to " + filename)
        if reset_:
            self.reset()
    
    def reset(self):
        print("RESETING")
        subprocess.Popen('say RESETING', shell=True).wait()
        self.last_packets = {} # key: ip addr, value: (time, data)
        self.collector = {}
        self.first_time = True
        self.run_flag = True
        self.start()

class WorkerCounter(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.second = 0
    
    def handle_timer(self):
        subprocess.Popen(f'say {self.second}', shell=True)
        self.second += 1
    
    def reset(self):
        self.second = 0
                
                
app = QCoreApplication(sys.argv)
timer = QTimer()
timer_counter = QTimer()
thread_csi = ThreadCSI()
thread_counter = QThread()
worker_counter = WorkerCounter()


def signal_handler(sig, frame):
    global timer, thread_csi
    timer.stop()
    thread_csi.ctrl_c(reset_=False)
    thread_csi.quit()
    exit(0)
signal.signal(signal.SIGINT, signal_handler)  

worker_counter.moveToThread(thread_counter)
timer.setInterval(1000//frequency)
timer.timeout.connect(thread_csi.handle_timer)
timer_counter.setInterval(1000//1)
timer_counter.timeout.connect(worker_counter.handle_timer)
thread_csi.process_started.connect(worker_counter.reset)

thread_csi.start()
thread_counter.start()
timer.start()
timer_counter.start()
app.exec()
