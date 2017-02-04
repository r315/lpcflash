#!/usr/bin/env python
# PyFlash.py
# a simple program to write a hex file into LPC1768 microcontroller flash memory
#
# Notes on ISP:
# ISP commands use on-chip RAM from 0x10000118 to 0x100001FF
# Flash programming commands use the top 32 bytes of on-chip RAM. 
# The stack is located at RAM top - 32. The maximum stack usage is 256 bytes and it grows downwards.
#

import serial, uu
import sys, getopt 
from sys import stdout


def exitApp(port):
	port.close()
	sys.exit(2)
	
# --------------- ISP Commands ---------------------
#note the commands assume that echo is disable !!

def go(com, address):
	com.write("G %d T\n" % address)
	return int(com.readline())   #return code	

def unlock(com):
	com.write("U 23130\n")
	return int(com.readline())   #return code
	
def blankCheck(com, start_sector, end_sector):
	com.write("I %d %d\n" % ( start_sector, end_sector ))
	code = int(com.readline())   #return code
	if code != 0:
		res1 = com.readline()        #response 1
		res2 = int(com.readline())   #response 2
		return code, res1, res2
	return code

def prepareSectors(com, start_sector, end_sector):
	com.write("P %d %d\n" % ( start_sector, end_sector ))
	return int(com.readline())   #return code
		
def eraseSectors(com, start_sector, end_sector):
	com.write("E %d %d\n" % ( start_sector, end_sector ))
	return int(com.readline())   #return code, TODO: check if will cause timeout
		
def copyRamToFlash(com, flashAddress, ramAddress, size): #size should be 256 | 512 | 1024 | 4096
	com.write("C %d %d %d\n" % ( flashAddress, ramAddress, size ))
	return int(com.readline())	
		
def connectDevice(com):
	devid = 0
	com.write(b'?')
	res = com.readline()
	if res == "Synchronized\r\n":
		com.write("Synchronized\n")
		com.readline()       #read echo
		res = com.readline() #read response
		if res == "OK\r\n":
			#print("Sync")
			com.write("12000\n")
			com.readline()
			res = com.readline()
			if res == "OK\r\n" :
				com.write("A 0\n") #disable echo
				com.readline()   #echo		
				com.readline()   #result
				com.write("J\n")
				#com.readline()   #echo
				com.readline()   #result
				devid = int(com.readline())
				print "Device ID","[" + format(devid, '#08X') + "]"
				com.write("K\n")
				com.readline()   #result
				major = int(com.readline())
				minor = int(com.readline())				
				print 'Boot Loader Version', '['+ str(major) + '.' + str(minor) +']'
				#printReturnCode(blankCheck(com, 0,0))		
	if devid == 0 :
		print 'No device detected'
		exitApp(com)
	elif devid != PARTID:
		print 'Error reading device'
		print 'Expected id ' + format(PARTID, '#08X') + ' Got ' + format(devid, '#08X')
		exitApp(com)	
		
# ---------- program functions -----------
def sendChecksum(com, data):
	sum = 0
	for x in data:
		sum += x
	com.write(("%s\n") % (sum))
	com.flush()
	print "Line Checksum: %d" % sum
	
def sendDataLine(com, data): #max data size 45 bytes
	#print "send line"
	cdata = uu.encode(data)
	com.write(cdata)
	com.write("\n") 
	com.flush()	
	#print cdata
	#time.sleep(0.05)
	
def sendDataBlock(com, address, data): #max data size 20*45 bytes
	data_len = len(data)
	if data_len > uu.blockSize:
		return 6				#count error
	com.write("W %d %d\n" % ( address, data_len))
	#com.flush()
	#com.readline()  #echo
	#com.readline()  #echo
	code = int(com.readline())	
	if code != 0:
		return code
	n = 0		
	while data_len > 0:
		bytes = data_len if data_len < uu.lineSize else uu.lineSize
		sendDataLine(com, data[n: n + bytes])
		n += uu.lineSize
		data_len -= uu.lineSize
	com.write(("%d\n") % uu.sum(data))
	com.flush()
	code = com.readline()
	com.flush()
	if code == "RESEND\r\n":
		return 20
	elif code == "OK\r\n":
		return 0

def writeRam(com, address, data):
	n = 0
	retries = 2
	data_len = len(data)
	while data_len > 0:	
		bytes = data_len if data_len < uu.blockSize else uu.blockSize
		code = sendDataBlock(com, address, data[n: n + bytes])
		if code == 20 : #resend code
			stdout.write('!')
			retries -= 1
			if retries == 0:
				return 20			
		else :
			n += uu.blockSize
			data_len -= uu.blockSize
			address += n
			stdout.write('.')  #send write block info
	stdout.write('\n')
	return code		

def readRam(com, address, size):
	com.write("R %d %d\n" % ( address, size ))
	code = int(com.readline()) # return code
	if code != 0:
		printReturnCode(code)
		return None		
	expected_lines = (size + uu.lineSize - 1) / uu.lineSize		
	data = []
	for i in range(0, expected_lines, uu.maxLines):
		lines = expected_lines - i
		if lines > uu.maxLines:
			lines = uu.maxLines
		cdata = []
		for i in range(0, lines):
			line = com.readline()
			line = line.replace("\r\n","")
			decoded = uu.decode(line)
			cdata += decoded
			
		s = int(com.readline())
		ds = uu.sum(cdata)
		if s != ds:
			print ("checksum mismatch on read got %x expected %x" % (s, ds) )
			exitApp(com)
		else:
			com.write("OK\r\n")			
		data += cdata
	return data

def printReturnCode(code):
def printReturnCode(code, prefix='', posfix=''):
	if code == 0 :
		print prefix, 'CMD_SUCCESS'
	elif code == 1 :
		print prefix, 'INVALID_COMMAND', posfix
	elif code == 2 :
		print prefix, 'SRC_ADDR_ERROR', posfix
	elif code == 3 :
		print prefix, 'DST_ADDR_ERROR', posfix
	elif code == 4 :
		print prefix, 'SRC_ADDR_NOT_MAPPED', posfix
	elif code == 5 :
		print prefix, 'DST_ADDR_NOT_MAPPED', posfix
	elif code == 6 :
		print prefix, 'COUNT_ERROR', posfix
	elif code == 7 :
		print prefix, 'INVALID_SECTOR', posfix
	elif code == 8 :
		print prefix, 'SECTOR_NOT_BLANK', posfix
	elif code == 9 :
		print prefix, 'SECTOR_NOT_PREPARED_FOR_WRITE_OPERATION', posfix
	elif code == 10 :
		print prefix, 'COMPARE_ERROR', posfix
	elif code == 11 :
		print prefix, 'BUSY', posfix
	elif code == 12 :
		print prefix, 'PARAM_ERROR', posfix
	elif code == 13 :
		print prefix, 'ADDR_ERROR', posfix
	elif code == 14 :
		print prefix, 'ADDR_NOT_MAPPED', posfix
	elif code == 15 :
		print prefix, 'CMD_LOCKED', posfix
	elif code == 16 :
		print prefix, 'CMD_SUCCESS', posfix
	elif code == 17 :
		print prefix, 'INVALID_CODE', posfix
	elif code == 18 :
		print prefix, 'INVALID_STOP_BIT', posfix				
	elif code == 19 :
		print prefix, 'CODE_READ_PROTECTION_ENABLED', posfix
	elif code == 20 :
		print prefix, 'RESEND', posfix
	return code
		
if __name__ == "__main__":
	PARTID = 0x26013f37
	APPNAME = 'Pyflash.py'
	APPHELP = " -p serial_port (-h hexfile | -b binfile)\n [-a loadaddress]\n"
	DLADDRESS = 0x10000200
	devid = 0
	try:
		opts, args = getopt.getopt(sys.argv[1:], "p:h:b:a:",["port=","hexfile="])
	except getopt.GetoptError:
		print "Bad parameters"
		print "Usage: ", APPNAME, APPHELP
		sys.exit(2)
		
	if len(opts) < 2:
		print "Missing parameter!"
		print "Usage: ", APPNAME, APPHELP
		sys.exit(2)		

	for opt, arg in opts:		
		if opt in ("-p", "--port"):
			serialport = arg
		elif opt in ("-h", "--hexfile"):
			print "-h, Not implemented yet!"
			sys.exit(1)
			#hexfile = arg
		elif opt in ("-b", "--binfile"):
			binfile = arg
		elif opt in ("-a", "--address"):
			try:
				DLADDRESS = int(arg,16)
			except Exception as ex:
				print ex
				sys.exit(1)
	try:
		com = serial.Serial(serialport, 19200, timeout = 1)
	except serial.SerialException:
		print 'Could not open ', serialport
		sys.exit(2)
		
	print "Opened Port:", com.name
	try :
		data = []		
		with open(binfile, "rb") as f:
			byte = f.read(1)
			while byte != "":
				data.append(ord(byte))
				byte = f.read(1)		
		print "Connecting to device.."
		connectDevice(com)
		print "Writing %d bytes to address 0x%X" % (len(data), DLADDRESS)
		printReturnCode(writeRam(com, DLADDRESS,data))
		unlock(com)
		go(com, DLADDRESS)
	except IOError as e :
		print "File open error({0}): {1}".format(e.errno, e.strerror)		
	com.close()

