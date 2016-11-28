import struct
import time

def bytes_to_str(s):
    return "-".join("{:02x}".format(ord(c)) for c in s)

def opcode_init(session, protocol, envid, key):
    data = struct.pack('<HLHBL' + str(len(key)) + 's',
                        1, 47, protocol, envid, len(key), key)
    print 'init>', bytes_to_str( data )
    session.send(data)
    data=session.recv(16)
    print 'init<', bytes_to_str(data)
    answer=struct.unpack('<HIBBB', data)
    if answer[0] != 1 or answer[3] != protocol:
        print "Wrong response"
        exit(1)

def opcode_ping(session):
    data = struct.pack('<HL', 0,0)
    print 'ping>', bytes_to_str(data)
    session.send(data)
    data = session.recv(16)
    print 'pong<', bytes_to_str(data)
