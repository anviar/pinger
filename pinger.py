#!/usr/bin/env python3

import socks
import argparse
import time,datetime,importlib

# Preparing arguments
argparser=argparse.ArgumentParser(description='Check service health')
argparser.add_argument('--host', help='hostname', type=str, required=True)
argparser.add_argument('--port', help='port', type=int, required=True)
argparser.add_argument('--protocol', help='protocol version', type=int, required=True)
argparser.add_argument('--key', help='client key', type=str, required=True)
argparser.add_argument('--envid', help='environment id', type=int, required=True)
#argparser.add_argument('--user', help='username', type=str, required=True)
#argparser.add_argument('--password', help='password', type=str, required=True)
args = argparser.parse_args()
print ( args )

# loading requested protocol
protocol = importlib.import_module( 'protocol.v' + str(args.protocol))

session = socks.socksocket()
session.set_proxy(socks.SOCKS4, args.host, 443)
session.connect(('127.0.0.1', args.port))

protocol.opcode_init(session, args.protocol,args.envid, args.key)
#protocol.opcode_login(session, args.user, args.password)
for i in range (0,5):
    start_time = datetime.datetime.now()
    protocol.opcode_ping(session)
    end_time = datetime.datetime.now()
    response_delay = (end_time - start_time).microseconds / 1000
    if response_delay > 500:
        print ( "Response time too long:", response_delay )
        exit(1)
    time.sleep(0.3)
session.close()