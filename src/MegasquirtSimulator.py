# Megasquirt Emulator
# Copyright Ben Tyreman (bentyreman@btinternet.com) 2010
# Dave Smith 2011
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from struct import pack, unpack, calcsize
import pickle
import time
import socket
import csv


host = "localhost"
port = 7893
buf = 1024
addr = (host,port)

class LogReader(csv.DictReader):
	def __init__(self, f, fieldnames=None, restkey=None, restval=None,dialect="excel-tab", *args, **kwds):
		csv.DictReader.__init__(self, f, fieldnames, restkey, restval, dialect)
		
	def next(self):
		if self.line_num == 1:
			self.signature = self._fieldnames[0]
			self._fieldnames = None
			# Used only for its side effect.
			self.fieldnames
			self.fixFieldNames()
		row = self.reader.next()
		self.line_num = self.reader.line_num

		# unlike the basic reader, we prefer not to return blanks,
		# because we will typically wind up with a dict full of None
		# values
		while row == []:
			row = self.reader.next()
		d = dict(zip(self.fieldnames, row))
		lf = len(self.fieldnames)
		lr = len(row)
		if lf < lr:
			d[self.restkey] = row[lf:]
		elif lf > lr:
			for key in self.fieldnames[lr:]:
				d[key] = self.restval
		return d
	
	def fixFieldNames(self):
		translateList=[['RPM/100','rpm100'],['SecL','secl'],['MAP','mapADC'],['TP','tpsADC']]
		for translation in translateList:
			if translation[0] in self._fieldnames:
				loc = self._fieldnames.index(translation[0])
				self._fieldnames[loc]=translation[1]
		pass

class MegasquirtSimulator:

	# Set the signature and version strings
	# These are found in the megasquirt ini file
	signature = "MS1/Extra format 029y3 *********"
	version = "T"


	def __init__(self):

		# Open and parse the megasquirt ini file
		self.open_ini()
		self.open_log()

		# Set some basic rtvars (Real Time Variables)
		# Names are the same as in the megasquirt ini file
		self.pulseWidth1 = 5.8
		self.advance = 20
		self.coolant = 212
		self.rpm = 3456
		self.batteryVoltage = 14.3
		self.advance = 20
		self.engine = 1
		self.barometer = 100
		self.map = 91
		self.mat = 77
		self.tps = 53
		self.afr1 = 14.71
		self.gammaEnrich = 100
		self.egoCorrection1 = 100
		self.egoCorrection2 = 100
		self.airCorrection = 100
		self.warmupEnrich = 100
		self.baroCorrection = 100
		self.veCurr1 = 49
		self.seconds = 0
	
	def run(self):
		
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.bind((host, port))
		self.s.listen(1)
		print "Waiting for connection"
		conn, addr = self.s.accept()
		
		
		print "Connection"
		
		while 1:
			data = conn.recv(1)
			if not data: break
			self.lastCommand = data
			response = self.generateResponse()
			conn.send(response)
		conn.close()
		
		
		
	def open_log(self):
		self.logFileName = sys.argv[1]
		self.logContents=[]
		
		logReader = LogReader(open(self.logFileName,'rb'),delimiter='\t')
		for row in logReader:
			self.logContents.append(row)
		
		#self.signature = logReader.signature
		pass
		
		
					
	def open_ini(self):
		# Ini file has a section called OutputChannels
		# Section contains all info on the rtvars array, as well as other information such as calculated fields
		# All rtvars start with "scalar", bit fields are broken down using "bits", other fields are calculated
		ini = "ecuDef/msns-extra.29y.ini"
		self.rtvars = {}	# Dictionary to hold rtvars, key is the memory address
		f = open(ini, "r")
		och_found = False
		for line in f.readlines():
			# Run through the ini file to find the output channels section
			if not och_found:
				if "[outputchannels]" in line.lower():
					och_found = True
				continue
			line = line.strip()
			if line == "": continue		# Blank line
			if line[0] == "[": break	# Moved on to next section in ini file
			line = line.split(";", 1)[0].strip()	# Strip comments
			if "scalar" in line.lower():		# Found a real time variable
				# Format of line is '<field name> = scalar, <type>, <rtvars memory address>, "<display unit>", <scale>, <offset>'
				line = [item.strip() for item in line.split(",")]
				name = line[0].split("=")[0].strip()
				type = line[1]
				# Convert type in ini file to type used by Python unpack
				if type == "U08":	# Unsigned byte
					type = "B"
				elif type == "S08":	# Signed byte
					type = "b"
				elif type == "U16":	# Unsigned 2 byte int
					type = "H"
				elif type == "S16":	# Signed 2 byte int
					type = "h"
				elif type == "U32":	# Unsigned 4 bit int
					type = "I"
				elif type == "S32":	# Signed 4 bit int
					type = "i"
				och = {"name": name,
				       "type": ">" + type,
				       "scale": float(line[4]),
				       "loc": int(line[2]),
				       "size": calcsize(type)}
				setattr(self, name, 0.0)
				self.rtvars[och["loc"]] = och
			if "ochBlockSize" in line:	# Found the size of the rtvars array
				line = [item.strip() for item in line.split("=")]
				self.ochBlockSize = int (line[1])
			if "queryCommand" in line:	# Found signature command
				line = [item.strip() for item in line.split("=")]
				self.queryCommand = line[1].replace('"','')
			if "ochGetCommand" in line:	# Found signature command
				line = [item.strip() for item in line.split("=")]
				self.ochGetCommand = line[1].replace('"','')
				
		f.close()

		try:
			data_file = open('flash.data', 'rb')
			self.flash = pickle.load(data_file)
		except:
			self.flash = {}		# Emulated flash tables
			# Initialise 20 tables
			# Shouldn't need more than that
			for i in range(1, 21):
				flash = {}
				for j in range(1024):
					flash[j] = "\x00"	# Initialise the data to blanks
				self.flash[i] = flash
		# Copy flash to ram
		self.tables = {}	# Emulated ram tables
		for i in range(1, len(self.flash) + 1):
			table = {}
			flash = self.flash[i]
			for j in range(1024):
				table[j] = flash[j]
			self.tables[i] = table

	def next(self):
		self.seconds += 100 	# Emulate the internal counter of the Megasquirt
		char = self.s.recv()	# Read a single char from the serial port
		if char != "A": print "Received '%s'" % char	# Prevent flooding the display with 'A' commands
		try:
			resp = getattr(self, "%s_command" % char)()
			if char != "A" and resp is not None: print "Returned data"
			if resp: self.tx(resp)
		except AttributeError:
			pass


	# S is the command to send the version string
	def S_command(self):
		return self.signature

	# Q is the command to send the signature string
	def Q_command(self):
		return self.signature

	# r is the command to read a table
	def A_command(self):
		# Next 6 bytes following the r char are 3 2 byte ints
		# These are the table number, the memory offset in that table, and the number of bytes to read
		(table_idx, offset, bytes) = unpack(">hhh", self.s.recv(6))
		print "Table ID = %d, Table offset = %d, Bytes to read = %d" % (table_idx, offset, bytes)
		string = ""
		# Attempt to find the data in the emulated tables memory
		try:
			table = self.tables[table_idx]
			for i in range(bytes):
				string += table[i]
		except KeyError:
			# Can't find the table, so fake the data with blanks
			for i in range(bytes):
				string += "\x00"
		return string

	# w is the command to write data
	def w_command(self):
		# Next 6 bytes following the w char are 3 2 byte ints
		# These are the table number, the memory offset in that table, and the number of bytes to write
		(table_idx, offset, bytes) = unpack(">hhh", self.s.recv(6))
		print "Table ID = %d, Table offset = %d, Bytes to write = %d" % (table_idx, offset, bytes)
		table = self.tables[table_idx]
		for i in range(offset, offset + bytes):
			table[i] = self.s.recv(1)	# Read a byte of data and store it in the table
		return

	# A is the command to return the real time variables array
	def R_command(self):
		return self.build_rtvars()

	# e is the command to write data with echo
	def e_command(self):
		# Next 6 bytes following the e char are 3 2 byte ints
		# These are the table number, the memory offset in that table, and the number of bytes to write
		(table_idx, offset, bytes) = unpack(">hhh", self.s.recv(6))
		print "Table ID = %d, Table offset = %d, Bytes to write = %d" % (table_idx, offset, bytes)
		string = ''
		table = self.tables[table_idx]
		for i in range(offset, offset + bytes):
			data = self.s.recv(1)	# Read a byte of data and store it in the table
			table[i] = data
			string += data
		return string

	# b is the command to burn the ram copy of a table to flash memory
	def b_command(self):
		# Next 2 bytes following the b char is the table number
		(table_idx,) = unpack(">h", self.s.recv(2))
		print "Table ID = %d" % table_idx
		self.flash[table_idx] = self.tables[table_idx]
		data_file = open('flash.data', 'wb')

	# t is the command to flash the coolant, mat, ego, maf, etc tables
	def t_command(self):
		# Next 2 bytes following the t char is the table number
		# Next 2048 bytes following that is the table data
		# Throw all of this away
		(table_idx,) = unpack(">h", self.s.recv(2))
		print "Table ID = %d" % table_idx
		self.s.recv(2048)


	# Build the rtvars array
	def build_rtvars(self):
		string = ""
		i = 0
		while i < self.ochBlockSize:
			if self.rtvars.has_key(i):
				item = self.rtvars[i]
			else:
				# Cannot find a variable to put into this memory space, so fill with blanks
				i += 1
				string += "\x00"
				continue
			i += item["size"]
			fmt = item["type"]
			val = getattr(self, item["name"])	# Get the variable from the class space
			scale = item["scale"]
			string += pack(fmt, int((val) / (scale)))
		return string

	def write(self, cmd):
		self.lastCommand = cmd

	def generateResponse(self):
		self.seconds += 100 	# Emulate the internal counter of the Megasquirt
		if self.lastCommand != "A": print "Received '%s'" % self.lastCommand	# Prevent flooding the display with 'A' commands
		try:
			resp = getattr(self, "%s_command" % self.lastCommand)()
			if self.lastCommand != "A" and resp is not None: print "Returned data"
			if resp:
				transmit_time = len(resp) * 10.0 / 9600.0
				time.sleep(transmit_time)
				return resp
		except AttributeError:
			pass

if __name__ == "__main__":
	MS = MegasquirtSimulator()
	MS.run()