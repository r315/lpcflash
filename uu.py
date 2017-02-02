
#uu encoding for NXP ISP

lineSize = 45
maxLines = 20
blockSize = lineSize * maxLines

def sum(data):
	s = 0
	for i in data:
		s += i
	return s

def decode(line):
	# uu encoded data has an encoded length first
	linelen = ord(line[0]) - 32
	
	uu_linelen = ((linelen + 3 - 1) / 3) * 4

	if uu_linelen + 1 != len(line):
		print("error in line length")
		
	# pure python implementation - if this was C we would
	# use bitshift operations here 
	decoded = []
	for i in range(1, len(line), 4):
		c = 0
		for j in line[i: i + 4]:
			ch = ord(j) - 0x20			
			ch %= 64
			c = (c * 64) + ch
		s = []
		for j in range(0, 3):
			s.append(c % 256)
			c /= 256
		for j in reversed(s):
			decoded.append(j)	
			
	return decoded[0:linelen] # only return real data
	
def uu_addpadding(data, padding):
	pad_size = len(data) % 3
	if pad_size != 0:
		for x in range(0, 3 - pad_size):
			data.append(padding)
	return data
	
def uu_transform(data):  # transform 3bytes
	sum  = 0             # in 4bytes of uu code
	uu_data = []
	for x in data:		
		sum *= 256  #shift left 8bit
		sum += x
		
	for x in range(0 , 4):		
		uu_data.append(sum % 64)
		sum /= 64   #shift right 6bit	
	#printdata(reversed(uu_data))
	return reversed(uu_data)
	
def encode(data):	
	uu_len = len(data)
	uu_addpadding(data,0)
	uu_data = []
	uu_data.append(uu_len)
	for x in range(0, uu_len, 3):  #steps in 3bytes
		uu_data.extend(uu_transform(data[x : x + 3]))	
	uu_code = ''
	for x in uu_data:
		if x == 0:
			x = 0x60
		else :
			x += 0x20
		uu_code += chr(x)
	return uu_code
	
def printdata(data):
	for d in data:
		print format(d,'#02X')

