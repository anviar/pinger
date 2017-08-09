#!/usr/bin/env python3

import socks
import argparse
import time,datetime,importlib

# Preparing arguments
argparser=argparse.ArgumentParser(description='Check service health')
argparser.add_argument('--host', help='hostname', type=str, required=True)
argparser.add_argument('--port', help='port', type=int, required=True)
argparser.add_argument('--protocol', help='protocol version', type=int, required=True)
argparser.add_argument('--ping', help='number of ping iterations, default 5', type=int, default=5)
argparser.add_argument('--timeout', help='timeout for socket operations, default 5', type=float, default=5)
argparser.add_argument('--ping-timeout', help='timeout for socket operations, default 5', type=int, default=2000)
argparser.add_argument('--key', help='client key', type=str, required=True)
argparser.add_argument('--envid', help='environment id', type=int, required=True)
argparser.add_argument('--user', help='username', type=str )
argparser.add_argument('--password', help='password', type=str)
args = argparser.parse_args()
print(args)

# loading requested protocol
protocol = importlib.import_module('protocol.v' + str(args.protocol))

session = socks.socksocket()
session.set_proxy(socks.SOCKS4, args.host, 443)
session.settimeout(args.timeout)
session.connect(('127.0.0.1', args.port))
protocol.opcode_init(session, args.protocol,args.envid, args.key)
if args.user is not None and args.password is not None:
    protocol.opcode_login(session, args.user, args.password)
for i in range(0, args.ping):
    start_time = datetime.datetime.now()
    protocol.opcode_ping(session)
    end_time = datetime.datetime.now()
    response_delay = (end_time - start_time).microseconds / 1000
    if response_delay > args.ping_timeout:
        print("Response time too long:", response_delay)
        exit(1)
    time.sleep(0.3)

if args.user is not None and args.password is not None:
    protocol.opcode_logout(session)
session.close()