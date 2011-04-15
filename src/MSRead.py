'''
Created on Apr 11, 2011

@author: dgs
'''
import serial
import time
x=1
# Open a serial port.
ser = serial.Serial("/dev/tty.MSDongle-DevB",
        baudrate = 9600,
        bytesize = serial.EIGHTBITS,
        parity = serial.PARITY_NONE,
        stopbits = serial.STOPBITS_ONE,
        xonxoff = 0, 
        rtscts = 0)

# Check for something in the buffer.
buffwaiting = (ser.inWaiting() != 0)
print ser.inWaiting()

ser.flushInput()
print ser.inWaiting()

ser.write('T')
print ser.inWaiting()
ser.write('T')
print ser.inWaiting()
ser.write('T')
print ser.inWaiting()
time.sleep(5)
print ser.inWaiting()

# Read the port.
sig=''
while(ser.inWaiting() > 0) :
    sreply = ser.read(1)
    print ser.inWaiting(),sreply
    sig=sig+sreply
    
print sig
# Close the port.
ser.close()
