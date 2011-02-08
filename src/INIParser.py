'''
Created on Oct 29, 2010

@author: dgs
'''
import re
from struct import pack, unpack, calcsize

class INIParser(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.expressions=[]
        self.rtvars={}
        
    def loadIni(self,iniFile):
        f = open('ecuDef/' + iniFile)
        self.rtvars = {}    # Dictionary to hold rtvars, key is the memory address
        och_found = False
        for line in f.readlines():
            # Run through the ini file to find the output channels section
            if not och_found:
                if "[outputchannels]" in line.lower():
                    och_found = True
            continue
            line = line.strip()
            if line == "": continue        # Blank line
            if line[0] == "[": break    # Moved on to next section in ini file
            line = line.split(";", 1)[0].strip()    # Strip comments
            if "scalar" in line.lower():        # Found a real time variable
                # Format of line is '<field name> = scalar, <type>, <rtvars memory address>, "<display unit>", <scale>, <offset>'
                line = [item.strip() for item in line.split(",")]
                name = line[0].split("=")[0].strip()
                type = line[1]
                # Convert type in ini file to type used by Python unpack
                if type == "U08":    # Unsigned byte
                    type = "B"
                elif type == "S08":    # Signed byte
                    type = "b"
                elif type == "U16":    # Unsigned 2 byte int
                    type = "H"
                elif type == "S16":    # Signed 2 byte int
                    type = "h"
                elif type == "U32":    # Unsigned 4 bit int
                    type = "I"
                elif type == "S32":    # Signed 4 bit int
                    type = "i"
                och = {"name": name,
                      "type": ">" + type,
                      "scale": float(line[4]),
                      "loc": int(line[2]),
                      "size": calcsize(type)}
                setattr(self, name, 0.0)
                self.rtvars[och["loc"]] = och
            if "ochBlockSize" in line:    # Found the size of the rtvars array
                line = [item.strip() for item in line.split("=")]
                self.ochBlockSize = int (line[1])
            if "ochGetCommand" in line:
                line = [item.strip() for item in line.split("=")]
                self.ochGetCommand = line[1].split('"')[1]
               
        f.close()



if __name__ == "__main__":

    IP = INIParser()
    IP.loadIni('msns-extra.29y.ini')
    for expr in IP.expressions:
        print expr