# ---------------------- config section ---------------------------------

port = 65432					# TCP port to listen on 
mac = "xx:xx:xx:xx:xx:xx" 		# BLE MAC address of your Yelight Candela

# -----------------------------------------------------------------------


import socket
import selectors
import types
import pygatt
import sys
import time
import string
import logging
import binascii

#logging.basicConfig()
#logging.getLogger('pygatt').setLevel(logging.DEBUG)

host = '0.0.0.0'

sel	= selectors.DefaultSelector()
lsock =	socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print('listening on', (host, port))
sys.stdout.flush()
lsock.setblocking(False)
sel.register(lsock,	selectors.EVENT_READ, data=None)

def	accept_wrapper(sock):
	conn, addr	= sock.accept()	 
	print('accepted connection	from', addr)
	sys.stdout.flush()
	conn.setblocking(False)
	data =	types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
	events	= selectors.EVENT_READ | selectors.EVENT_WRITE
	sel.register(conn,	events,	data=data)
	return conn
	
def	service_connection(key,	mask):
	global clients
	sock =	key.fileobj
	data =	key.data
	if	mask & selectors.EVENT_READ:
		recv_data	= sock.recv(1024)  
		if recv_data:
			return recv_data
			data.outb +=	recv_data
		else:
			print('closing connection to', data.addr)
			sys.stdout.flush()
			sel.unregister(sock)
			sock.close()
			clients.remove(sock)
			return False

def status_handler(handle, value):
	global flickerStat, flickerMode, restartFlicker, on, brightness, ack, key, mask, clients
	print("handle:" + str(handle))
	valstr = binascii.hexlify(bytearray(value))
	print("value :" + str(valstr.decode('utf8')))
	sys.stdout.flush()
	if value[1] == 0x45:
		if value[2] == 0x02:
			on = False
			flickerStat = False
			print('STATUS: OFF')
		elif value[2] == 0x01:
			on = True
			flickerStat = False
			print('STATUS: ON')
		brightness = int(value[3])
		print('BRIGHTNESS: ' + str(brightness))
		sys.stdout.flush()
	if value[1] == 0x63: 
		if value[2] == 0x01: 
			flickerStat = True
			on = True
			print('FLICKER: ON')
		elif value[2] == 0x03:
			if not flickerMode:
				flickerStat = False
				restartFlicker = False
				print('FLICKER: OFF')
			else:
				restartFlicker = True
				print('Continue FLICKER')
	if not restartFlicker:
		ack = ack + 1
	sock =	key.fileobj
	msg = str(on) + '|' + str(flickerStat) + '|' + str(brightness) + '\n'
	for client in clients :
		client.send(msg.encode())
	sys.stdout.flush()
	

def connect(adapter, mac):
	from time import sleep 
	t = 3
	i = 1
	while True:
		print('Connecting...')
		try:
			adapter.start()
			device = adapter.connect(mac,5)
			device.subscribe('8f65073d-9f57-4aaa-afea-397d19d5bbeb', callback = status_handler)
			print("SUCCESS (" + str(i) + ')')
			sys.stdout.flush()
			return device
		except:
			e = sys.exc_info()[0]
			print('ERROR ('+ str(i) + '): %s' %e)
		sys.stdout.flush()
		i = i + 1
		if t < 180:
			t = t * 2
		else:
			t = 180
		sleep(t)

adapter	= pygatt.GATTToolBackend()
device	= connect(adapter, mac)

# Init variables
flickerStat = False
flickerMode = False
restartFlicker = False
on = False
brightness = False
ack = 0
lastack = 0
waitForAck = False
repeat = False
clients = []
n = 0

while True:
	try:
		events	= sel.select(timeout=None)
		for key, mask in events:
			if key.data is None:
				c = accept_wrapper(key.fileobj)
				clients.append(c)
			else:
				cmd = service_connection(key, mask)
				if ((cmd and cmd != None) or repeat or restartFlicker): 
					tCmd = int(round(time.time()))
					lastack = ack
					if repeat:
						cmd = lastcmd
						repeat = False
					elif restartFlicker:
						device	= connect(adapter, mac)
						tCmd = int(round(time.time()))
						cmd = 'flicker'
						restartFlicker = False
					else:
						cmd	= str(cmd.decode(encoding='UTF-8',errors='ignore'))
						cmd	= cmd.strip()
						cmd = cmd.lower()
						lastcmd = cmd
					if cmd == "flicker":
						print("Command: FLICKER")
						sys.stdout.flush()
						flickerMode = True
						try:
							device.char_write_handle(0x001f,	bytearray([0x43, 0x40, 0x01])) #on
							device.char_write_handle(0x001f, bytearray([0x43,	0x67, 0x02]))
						except pygatt.exceptions.NotConnectedError:
							device	= connect(adapter, mac)
							tCmd = int(round(time.time()))
							device.char_write_handle(0x001f,	bytearray([0x43, 0x40, 0x01])) #on
							device.char_write_handle(0x001f, bytearray([0x43,	0x67, 0x02]))
					elif cmd ==	"on":
						print("Command: ON")
						sys.stdout.flush()
						try:
							if on:
								waitForAck = False
							else:
								device.char_write_handle(0x001f,	bytearray([0x43, 0x40, 0x01])) #on
								waitForAck = True
						except	pygatt.exceptions.NotConnectedError:
							device	= connect(adapter, mac)
							device.char_write_handle(0x001f,	bytearray([0x43, 0x40, 0x01])) #on
							waitForAck = True
					elif cmd ==	"reconnect":
						print("Command: RECONNECT")
						sys.stdout.flush()
						waitForAck = False
						device	= connect(adapter, mac)
					elif cmd ==	"off":
						print("Command: OFF")
						sys.stdout.flush()
						flickerMode = False
						try:
							device.char_write_handle(0x001f, bytearray([0x43, 0x42, brightness])) 
							device.char_write_handle(0x001f,	bytearray([0x43, 0x40, 0x02])) #off
							waitForAck = True
						except	pygatt.exceptions.NotConnectedError:
							device	= connect(adapter, mac)
							tCmd = int(round(time.time()))
							device.char_write_handle(0x001f, bytearray([0x43, 0x42, brightness]))
							device.char_write_handle(0x001f,	bytearray([0x43, 0x40, 0x02])) #off
							waitForAck = True
					elif cmd ==	"stop":
						print("Command: STOP FLICKER")
						sys.stdout.flush()
						flickerMode = False
						try:
							device.char_write_handle(0x001f, bytearray([0x43, 0x42, brightness])) 
							waitForAck = True
						except	pygatt.exceptions.NotConnectedError:
							device	= connect(adapter, mac)
							tCmd = int(round(time.time()))
							device.char_write_handle(0x001f, bytearray([0x43, 0x42, brightness]))
							waitForAck = True
					elif cmd.isdigit():
						intensity = int(cmd)
						print("Command INTENSITY:" + str(intensity))
						sys.stdout.flush()
						if intensity >= 0 & intensity <= 100:
							flickerMode = False
							try:
								if not on:
									device.char_write_handle(0x001f, bytearray([0x43, 0x40, 0x01])) #on
								device.char_write_handle(0x001f, bytearray([0x43, 0x42, intensity])) #intensiy
								waitForAck = True
							except pygatt.exceptions.NotConnectedError:
								device	= connect(adapter, mac)
								tCmd = int(round(time.time()))
								if not on:
									device.char_write_handle(0x001f, bytearray([0x43, 0x40, 0x01])) #on
								device.char_write_handle(0x001f, bytearray([0x43, 0x42, intensity])) #intensiy
								waitForAck = True
					else:
						waitForAck = False
			sys.stdout.flush()
		if (ack > lastack):
			print(str(lastcmd) + ' ACK (' + str(ack) + '|' + str(t) + ')')
			lastack = ack
			waitForAck = False
		elif waitForAck:
			t = int(round(time.time()))
			if t - tCmd > 2:
				n = n + 1
				if n<=3:
					repeat = True
					print('No ACK. Repeat command: ' + str(lastcmd))
					waitForAck = False
				else:
					n=0
		sys.stdout.flush()
	except KeyboardInterrupt:
		adapter.stop()
		lsock.close()
		raise
	except:
		e = sys.exc_info()[0]
		print( "EXCEPTION: %s" % e )
		sys.stdout.flush()
