# candela_socket_server
Control Yeelight Candela via TCP and BLE

This is ALPHA software. Use at own risk.

Installation:

Download the python file and configure TCP Port and BT MAC address at the top of the file.
Make yure you have the BLUEZ stack installed and a BLE adapter connected, which is able to detect your Yeelight Candela device.

After that you can give it a try like this:

python3 candela_server.py

This opens port 65432 for incoming connection. So you can now open a second shell and try:

telnet <IP-where-candela_server.py_is running> 65432

Now you can send the following command:

on => switch on
off => switch off
0-100 => sets intensity
flicker => starts flicker mode
reconnect => reconnects (usually not needed, as all other commands ensures, that connection is build up)

The Python scripts will send a response via the TCP socket like this

Power-Status|Flicker-Status|Intensity

e.g. 1|0|50 means Candela is switched on, flicker mode is off, intensity is at 50%
