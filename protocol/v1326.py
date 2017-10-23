import struct

errors = [
    'NONE',
    'BAD_DATA',
    'DB_ERROR',
    'SERVER_ERROR',
    'ALREADY_EXISTS',
    'NOT_FOUND',
    'FILE_SAVE_ERROR',
    'FILE_NOT_FOUND',
    'MUST_BE_LOGGED',
    'MUST_NOT_BE_LOGGED',
    'DB_CONNECTION_ERROR',
    'CACHE_ERROR',
    'TEAM_NAME_CAN_NOT_BE_EMPTY',
    'DISPLAY_NAME_CAN_NOT_BE_EMPTY',
    'EMAIL_CAN_NOT_BE_EMPTY',
    'INVALID_EMAIL_FORMAT',
    'PASSWORD_CAN_NOT_BE_EMPTY',
    'RECORD_NOT_FOUND',
    'DISCONNECTED',
    'EMAIL_ALREADY_EXISTS',
    'SEND_EMAIL',
    'OPCODE_NOT_FOUND',
    'BLOCKED',
    'REMOVED',
    'CLIENT_BLOCKED',
    'ARRAY_SIZE_TOO_BIG',
]


def bytes_to_str(s):
    return "-".join("{:02x}".format(ord(chr(c))) for c in s)


def opcode_pdf_pinger(session, recipients, timestamp):
    print('pdf_ping>', end=" ")
    recipients_str = ','.join(recipients)
    payload = struct.calcsize('<II' + str(len(recipients_str)) + 's')
    data = struct.pack('<HIII' + str(len(recipients_str)) + 's',
                       80, payload, timestamp,
                       len(recipients_str), bytes(recipients_str, 'UTF-8'))
    print(bytes_to_str(data))
    session.send(data)
    print('pdf_ping<', end=" ", flush=True)
    data = session.recv(64)
    print(bytes_to_str(data))
    data_info = struct.unpack('<HI', data[:6])
    if data_info[0] != 80:
        print("Wrong response")
        exit(1)
    data_parsed = struct.unpack('<HI' + str(data_info[1]) + 'b', data)
    if data_parsed[2] != 0:
        print("PDF ping error: %s" % errors[data_parsed[2]])
        exit(1)


def opcode_init(session, protocol, envid, key):
    data = struct.pack('<HIHBI' + str(len(key)) + 's',
                        1,
                        struct.calcsize('<HBI' + str(len(key)) + 's'),
                        protocol,
                        envid,
                        len(key),
                        bytes(key,'UTF-8'))
    print('init>', end=" ")
    session.send(data)
    print(bytes_to_str(data))
    print('init<', end=" ")
    data = session.recv(16)
    print(bytes_to_str(data))
    answer = struct.unpack('<HIBBB', data)
    if answer[0] != 1:
        print("Wrong response")
        exit(1)
    elif answer[2] != 0:
        print('Error: %s, expected proto: %s' % (errors[answer[2]], answer[3]))
        exit(1)

def opcode_ping(session):
    data = struct.pack('<HI', 0,0)
    print('ping>', end=" ")
    session.send(data)
    print(bytes_to_str(data))
    print('pong<', end=" ")
    data = session.recv(16)
    print(bytes_to_str(data))
    data_size = struct.unpack('<HI', data[:6])[1]
    data_parsed = struct.unpack('<HI' + str(data_size) + 'b', data)
    #print(data_parsed)


def opcode_login(session, username, password):
    print('login>', end=" ")
    data = struct.pack('<HII' + str(len(username)) + 'sI' + str(len(password)) + 's',
                        3,
                        struct.calcsize('<I' + str(len(username)) + 'sI' + str(len(password)) + 's'),
                        len(username), bytes(username, 'UTF-8'),
                        len(password), bytes(password, 'UTF-8'))
    print(bytes_to_str(data))
    session.send(data)
    print('login<', end=" ")
    data = session.recv(64)
    print(bytes_to_str(data))
    data_info = struct.unpack('<HI', data[:6])
    if data_info[0] != 3:
        print("Wrong response")
        exit(1)
    data_parsed = struct.unpack('<HI' + str(data_info[1]) + 'b', data)
    if data_parsed[1] == 1:
        print("Login error: %s" % errors[data_parsed[2]])
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
        print("Logout error: %s" % errors[data_parsed[2]])
        exit(1)
