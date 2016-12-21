import struct

def bytes_to_str(s):
    return "-".join("{:02x}".format(ord(chr(c))) for c in s)

def opcode_init(session, protocol, envid, key):
    data = struct.pack('<HIHBI' + str(len(key)) + 's',
        1,
        struct.calcsize('<HBI' + str(len(key)) + 's'),
        protocol,
        envid,
        len(key),
        bytes(key,'UTF-8'))
    print ( 'init>', end=" ")
    session.send(data)
    print (bytes_to_str( data ) )
    print('init<', end=" ")
    data=session.recv(16)
    print ( bytes_to_str(data) )
    answer=struct.unpack('<HIBBB', data)
    if answer[0] != 1 or answer[3] != protocol:
        print ( "Wrong response" )
        exit(1)

def opcode_ping(session):
    data = struct.pack('<HI', 0,0)
    print ( 'ping>', end=" ")
    session.send(data)
    print ( bytes_to_str(data) )
    print ('pong<', end=" ")
    data = session.recv(16)
    print ( bytes_to_str(data) )
    data_size = struct.unpack('<HI', data[:6])[1]
    struct.unpack('<HI' + str(data_size) + 'b', data)

def opcode_login(session, username, password):
    print('login>', end=" ")
    data = struct.pack('<HII' + str(len(username)) + 'sI' + str(len(password)) + 's',
                        3,
                        struct.calcsize('<I' + str(len(username)) + 'sI' + str(len(password)) + 's'),
                        len(username), bytes(username, 'UTF-8'),
                        len(password), bytes(password, 'UTF-8'))
    print ( bytes_to_str(data) )
    session.send(data)
    print('login<', end=" ")
    data = session.recv(64)
    print ( bytes_to_str(data) )
    data_info = struct.unpack('<HI', data[:6])
    if data_info[0] != 3:
        print("Wrong response")
        exit(1)
    data_parsed = struct.unpack('<HI' + str(data_info[1]) + 'b', data)
    if data_parsed[1] == 1:
        print("Login failed, error code", data_parsed[2])
        exit(1)

def opcode_logout(session):
    print('logout>', end=" ")
    data = struct.pack('<HI', 4, 0)
    print(bytes_to_str(data))
    session.send(data)
    print('logout<', end=" ")
    data = session.recv(64)
    print(bytes_to_str(data))
    data_info = struct.unpack('<HI', data[:6])
    if data_info[0] != 4:
        print("Wrong response")
        exit(1)
    data_parsed = struct.unpack('<HI' + str(data_info[1]) + 'b', data)
    if data_parsed[2] != 0:
        print("Logout failed")
        exit(1)