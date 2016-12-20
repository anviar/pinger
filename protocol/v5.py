import struct

def bytes_to_str(s):
    return "-".join("{:02x}".format(ord(chr(c))) for c in s)

def opcode_init(session, protocol, envid, key):
    data = struct.pack('<HLHBL' + str(len(key)) + 's',
                        1, 47, protocol, envid, len(key), bytes(key,'UTF-8'))
    print ( 'init>', bytes_to_str( data ) )
    session.send(data)
    data=session.recv(16)
    print ( 'init<', bytes_to_str(data) )
    answer=struct.unpack('<HIBBB', data)
    if answer[0] != 1 or answer[3] != protocol:
        print ( "Wrong response" )
        exit(1)

def opcode_ping(session):
    data = struct.pack('<HL', 0,0)
    print ( 'ping>', bytes_to_str(data) )
    session.send(data)
    data = session.recv(16)
    print ( 'pong<', bytes_to_str(data) )
    data_size = struct.unpack('<HL', data[:6])[1]
    struct.unpack('<HL' + str(data_size) + 'b', data)

def opcode_login(session, username, password):
    print('login>', end=" ")
    data = struct.pack('<HI' + str(len(username)) + 'sI' + str(len(password)) + 's',
                        3,
                        len(username), bytes(username, 'UTF-8'),
                        len(password), bytes(password, 'UTF-8'))
    print ( bytes_to_str(data) )
    session.send(data)
    print('login<', end=" ")
    data = session.recv(1)
    print ( bytes_to_str(data) )
    #data_size = struct.unpack('<HL', data[:6])[1]
    #truct.unpack('<HL' + str(data_size) + 'b', data)