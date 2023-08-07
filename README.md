# CSI Collection
CSI Collection using Nexmon CSI Project

</br>

<p align="center">
<img src="resources/CSIPlot.jpeg" alt="CSIPlot.jpeg"
title="CSIPlot.jpeg" width="900" align="middle" />
</p>

</br>

## Passive Sniffing
To start collecting CSI use the [Nexmon CSI project](http://https://github.com/seemoo-lab/nexmon_csi "Nexmon CSI project") and install it on a Raspberry Pi 4.

Connect you raspberry Pi to a router using an **ethernet cable** (the raspberry will loose the WiFi capability when running the Nexmon project).

Then transfer the `setup.sh` script into the raspberry pi and run it using the following command tostart collecting the CSI data.

```bash
sudo bash setup.sh --laptop-ip <ip> --raspberry-ip <ip> --mac-adr <MAC> --channel <channel> --bandwidth <bandwidth> --core <core> --spatial-stream <spatial stream>
```

 - The --laptop-ip is the ip of the laptop wants to collect data, this laptop must be connected to the same router as the raspberry.
 **Note** you can also collect the csi inside the raspberry instead of rerouting the packets to another laptop.
 - The --raspberry-ip is the ip of the raspberry pi.
 - The --mac-adr is the MAC address of the transmitter you want to filter.
 - --channel, --bandwidth, --core, and --spatial-stream are the CSI collection specifications (read more from Nexmon CSI project)

## CSI Collection
To collect the sniffed CSI data you can use the tcp dump command on the raspberry pi. if you used the --laptop-ip option in the above command you can also use the `collect_fixedrate_cam.py` script on you laptop.

```bash
python3 collect_fixedrate_cam.py --frequency <frequency> --packetnum <packetnum> --numcameras <numcameras>
```

 - --frequency is the frequency you wish to collect the CSI data.
 - --packetnum is the number of packets you wish to collect (you can terminate the process using ctrl+c at anytime you wish as well)
 - --numcameras is the number of cameras in case you want to record the environment with cameras as well as the CSI. (you can specify 0 if there is no need)

**NOTE** After the process, the raw CSI data (binary) will be saved into your workspace (read the next section) in a *.dat* file.

**NOTE** the `collect_fixedrate_cam.py` also can be used using multiple number of sniffers, it handles the synchronization and data collection automatically with no changes needed.


## CSI Parsing and Visualization
To parse or visualize the binary data collected in the previous section, you can use the `binary_to_complex.py` python script.

```bash
python3 binary_to_complex.py --file <filename.dat> --savecomplex --plot --saveplot
```

 - --file specifies the filename.dat collected using the previous section.
 -  --savecomplex saves the collected CSI complex numbers in a .cmplx file which which you can read it using python pickle.
 - --plot shows the plot of the amplitude of the CSI data.
 - --saveplot saves the plot in a jpeg file in your workspace

**NOTE** you can use --folder instead of --file to specify a directory to this script, in this case the script automatically finds all the .dat files inside that directory and process them with respect to --savecomplex and ----saveplot options (the --plot won't work when using --folder).




