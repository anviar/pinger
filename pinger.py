#!/usr/bin/env python

import socks
import argparse
import time,datetime

# Preparing arguments
argparser=argparse.ArgumentParser(description='Check service health')
argparser.add_argument('--host', help='hostname', type=str, required=True)
argparser.add_argument('--port', help='port', type=int, required=True)
argparser.add_argument('--protocol', help='protocol version', type=int, required=True)
argparser.add_argument('--key', help='client key', type=str, required=True)
argparser.add_argument('--envid', help='environment id', type=int, required=True)
args = argparser.parse_args()

# loading requested protocol
protocol = __import__('protocol.v' + str(args.protocol), globals(), locals(), ['object'], -1)

session = socks.socksocket()
session.set_proxy(socks.SOCKS4, args.host, 443)
session.connect(('127.0.0.1', args.port))

protocol.opcode_init(session, args.protocol,args.envid, args.key)
for i in range (0,5):
    start_time = datetime.datetime.now()
    protocol.opcode_ping(session)
    end_time = datetime.datetime.now()
    response_delay = (end_time - start_time).microseconds / 1000
    if response_delay > 90:
        print "Response time too long:", response_delay
        print args
        exit(1)
    time.sleep(0.3)
session.close()