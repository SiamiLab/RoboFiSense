import socket
import signal
import sys
import time 
import pickle
from datetime import datetime
import typing
from PyQt6.QtCore import QThread, QTimer, QCoreApplication, QMutex, QObject, pyqtSignal
import numpy as np
import os
import argparse
import cv2

parser = argparse.ArgumentParser()
parser.add_argument("--frequency", type=int, help="frequency to store CSI data", required=True)
parser.add_argument("--packetnum", type=int, help="number of packets to receive", required=True)
parser.add_argument("--numcameras", type=int, help="number of packets to receive", required=True)
args = parser.parse_args()

frequency = args.frequency
num_of_packets_to_collect = args.packetnum
num_of_cams = args.numcameras

mutex = QMutex()

class ThreadCSI(QThread):
    save_process_finish = pyqtSignal(str)
    def __init__(self) -> None:
        super().__init__()
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.bind(("", 5500))
        
        self.last_packets = {} # key: ip addr, value: (time, data)
        self.collector = {}
        self.run_flag = True
                    
    def run(self) -> None:
        first_time = True
        while self.run_flag:
            data, addr = self.client.recvfrom(4096)
            self.last_packets[addr[0]] = (time.time_ns(), data)
            if first_time:
                print("don't worry I'm receiving some stuff")
                first_time = False
    
    def handle_timer(self):
        if not self.run_flag:
            return
        for key, value in self.last_packets.items(): # key: ip addr, value: (time, data)
            if not key in self.collector.keys():
                self.collector[key] = {}
            if len(self.collector[key].keys()) < num_of_packets_to_collect:
                self.collector[key][value[0]] = value[1]
        if np.all(np.array([len(self.collector[key].keys()) for key in self.collector.keys()]) >= num_of_packets_to_collect) and len(self.collector.keys()) != 0:
            self.ctrl_c()
            
    def ctrl_c(self):
        self.run_flag = False
        mutex.lock()
        print('\nnumber of collectors: ' + str(len(self.collector)))
        for key in self.collector.keys():
            print(f' - number of samples from {key} is: ' + str(len(self.collector[key])))
        response = input("Do you want to save the CSI data? [y/n]")
        if response.upper() == 'Y' or response.upper() == "YES":
            print('Writing data to file. please wait!')
            filename = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")+'_csi.dat'
            pickle_out = open(filename,"wb")
            pickle.dump(self.collector, pickle_out)
            pickle_out.close()
            print("Done. Saved to " + filename)
        mutex.unlock()
        self.save_process_finish.emit("CSI")   

       
class WorkerCamera(QObject):
    save_process_finish = pyqtSignal(str)
    def __init__(self) -> None:
        super().__init__()
        self.collector = {i: [] for i in range(num_of_cams)}
        self.resolution = (2560, 720)
        self.cams = []
        for i in range(num_of_cams):
            self.cams.append(cv2.VideoCapture(i))
            self.cams[-1].set(cv2.CAP_PROP_FPS, frequency) # does not work
            self.cams[-1].set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cams[-1].set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        print('Camera setup finished')
        self.run_flag = True
    
    def handle_timer(self):
        if not self.run_flag:
            return
        for i in range(num_of_cams):
            ret, frame = self.cams[i].read()
            self.collector[i].append(frame)
        if np.all([len(self.collector[key]) == num_of_packets_to_collect for key in self.collector.keys()]) and len(self.collector.keys()) != 0:
            self.ctrl_c()
            
    def ctrl_c(self):
        self.run_flag = False
        mutex.lock()
        print('\nnumber of collectors: ' + str(len(self.collector)))
        for key in self.collector.keys():
            print(f' - number of samples from {key} is: ' + str(len(self.collector[key])))
        response = input("Do you want to save the CAM data? [y/n]")
        if response.upper() == 'Y' or response.upper() == "YES":
            print('Writing data to file. please wait!')
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            time_name = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            for i in range(num_of_cams):
                filename = time_name + f'_cam{i}.mov'
                writer = cv2.VideoWriter(filename, fourcc, frequency, self.resolution)
                for frame in self.collector[i]:
                    writer.write(frame)
                writer.release()
                self.cams[i].release()
                print("Done. Saved to " + filename)
        mutex.unlock()
        self.save_process_finish.emit("CAM")
    
    

                   
                
app = QCoreApplication(sys.argv)
timer = QTimer()
thread_csi = ThreadCSI()
thread_camera = QThread()
worker_camera = WorkerCamera()

finished = []
def handle_finished(txt):
    finished.append(txt)
    if "CSI" in finished and "CAM" in finished:
        exit(0)

def signal_handler(sig, frame):
    global timer, thread_csi
    timer.stop()
    thread_csi.ctrl_c()
    worker_camera.ctrl_c()
    thread_csi.quit()
    thread_camera.quit()       
signal.signal(signal.SIGINT, signal_handler)  

worker_camera.moveToThread(thread_camera)
timer.setInterval(1000//frequency)
timer.timeout.connect(thread_csi.handle_timer)
timer.timeout.connect(worker_camera.handle_timer)
thread_csi.save_process_finish.connect(handle_finished)
worker_camera.save_process_finish.connect(handle_finished)

thread_csi.start()
thread_camera.start()
timer.start()
app.exec()
