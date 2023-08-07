import pickle
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sys
import os
import ctypes
import signal
import argparse
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("--file", type=str, help="hex filename.dat to convert")
parser.add_argument("--folder", type=str, help="folder with .dat files inside (folder to folder is allowed)")
parser.add_argument("--plot", help="plot the file (only if --file specified)", action="store_true")
parser.add_argument("--saveplot", help="save the plot(s) (works for both file and folder)", action="store_true")
parser.add_argument("--savecomplex", help="save the complex format of .dat files (works for both file and folder)", action="store_true")
args = parser.parse_args()

def binary_to_complex(collector: dict):
    subcarriers_num = (len(collector[list(collector.keys())[0]]) - 18) // 4 # 18 is the number of bytes in leading information & each subcarrier has 4 bytes

    complex_csi = np.zeros((len(collector), subcarriers_num), dtype=complex)
    RSS = np.zeros((len(collector), 1), dtype=np.int8)
    row = 0
    for time, packet in collector.items():
        magic_bytes = packet[0:2].hex()
        rssi = packet[2:3].hex()
        rssi = ctypes.c_int8(int(rssi, 16)).value
        frame_control = packet[3:4].hex()
        source_mac = packet[4:10].hex()
        sequence_number = packet[10:12].hex()
        core_spatial = packet[12:14].hex()
        chanspec = packet[14:16].hex()
        chip_version = packet[16:18].hex()
        csi = packet[18:]
        complex_csi[row] = np.array([complex(int.from_bytes(csi[start:start+2], 'little', signed=True), int.from_bytes(csi[start+2:start+4], 'little', signed=True)) for start in range(0, 1024, 4)], dtype=complex)
        RSS[row] = rssi
        row += 1
        
    time_stamp_ns = np.array(list(collector.keys()))
    time_stamp_ns = time_stamp_ns - time_stamp_ns[0]
    
    return (time_stamp_ns, complex_csi, RSS)
    
        
def sve_complex_to_csv(filename: str, time_stamp_ns: np.ndarray, complex_csi: np.ndarray):
    df = pd.DataFrame(data=complex_csi, index=time_stamp_ns, columns=np.arange(1, 257, 1))
    df.to_csv(os.path.splitext(filename)[0]+'.csv')  


def plot_complex_csi(ax, time_stamp_ns: np.ndarray, complex_csi: np.ndarray, max=3000, title='CSI'):
    amp = abs(complex_csi)
    num_of_subcarriers = amp.shape[1]
    if num_of_subcarriers == 256: # 80 Mhz collection
        amp = np.delete(amp, [0, 1, 2, 3, 4, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 253, 254, 255], axis=1)
    else:
        print(f"WARNING: pilot and unused subcarrier removal is not implemented for {num_of_subcarriers} subcarriers, using thresholding instead ...")
        amp[amp >= max] = 0
    
    # x labels
    places = np.round(np.linspace(0, len(time_stamp_ns) - 1, 15)).astype(int)
    ax.set_xticks(places, (time_stamp_ns[places]/1e09).astype(int), rotation='horizontal', fontsize=10, fontweight='regular')
    ax.imshow(amp.T, interpolation="nearest", aspect="auto")
    ax.set_title(title)
    ax.set_xlabel("time (s)", fontsize=12, fontweight='regular')
    ax.set_ylabel("subcarrier", fontsize=12, fontweight='regular')


def process_file(file: str, savecomplex: bool, plot:bool, saveplot: bool):
    pickle_in = open(file, "rb")
    collectors = pickle.load(pickle_in)
    pickle_in.close()
    
    collector_complex = []
    for collector_ip, collector in collectors.items():
        time_stamp_ns, complex_csi, RSS = binary_to_complex(collector)
        collector_complex.append({"collector_ip": collector_ip, "time_stamp_ns": time_stamp_ns, "complex_csi": complex_csi, "RSS": RSS})
        
    if savecomplex:
        pickle_out = open(os.path.splitext(file)[0] + ".cmplx", "wb")
        pickle.dump(collector_complex, pickle_out)
        pickle_out.close()
    
    if plot or saveplot:
        fig, axes = plt.subplots(nrows=len(collector_complex), ncols=1)
        if len(collector_complex) == 1:
            axes = [axes]
        ax_cnt = 0
        for csi in collector_complex:
            ax = axes[ax_cnt]
            plot_complex_csi(ax, csi['time_stamp_ns'], csi['complex_csi'], max=3000, title=csi['collector_ip'])
            ax_cnt += 1
        plt.tight_layout()
    if saveplot:
        plt.savefig(os.path.splitext(file)[0] + '.jpeg', dpi=1500)
        plt.clf()
        plt.close()
    if plot:
        plt.show()

if args.file is not None:
    process_file(args.file, args.savecomplex, args.plot, args.saveplot)

elif args.folder is not None: 
    folder = os.path.abspath(args.folder)
    found_files = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".dat"):
                found_files.append(os.path.join(root, file))
    # print('\n'.join([elem for elem in found_files]))

    for file in tqdm(found_files):
        process_file(file, args.savecomplex, False, args.saveplot)
    

    