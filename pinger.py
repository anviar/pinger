#!/usr/bin/env python3

import socks
from argparse import ArgumentParser
import time
import datetime
import importlib
import yaml
import os

workdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(workdir, "config.yml"), 'r') as config_obj:
    config = yaml.load(config_obj)

# Preparing arguments
argparser = ArgumentParser(description='Check service health')
argparser.add_argument('--service',
                       help='service name',
                       choices=[str(s) for s in config['services']],
                       required=True)
args = argparser.parse_args()
print(config['services'][args.service])

# loading requested protocol
protocol = importlib.import_module('protocol.v' + str(config['services'][args.service]['protocol']))

session = socks.socksocket()
session.set_proxy(socks.SOCKS4, config['services'][args.service]['host'], 443)
session.settimeout(config['services'][args.service]['timeout'])
session.connect(('127.0.0.1', config['services'][args.service]['port']))
protocol.opcode_init(
    session,
    config['services'][args.service]['protocol'],
    config['services'][args.service]['envid'],
    str(config['services'][args.service]['key']))
protocol.opcode_login(
    session,
    config['services'][args.service]['user'],
    config['services'][args.service]['password'])
for i in range(0, config['services'][args.service]['ping']):
    start_time = datetime.datetime.now()
    protocol.opcode_ping(session)
    end_time = datetime.datetime.now()
    response_delay = (end_time - start_time).microseconds / 1000
    if response_delay > config['services'][args.service]['ping-timeout']:
        print("Response time too long:", response_delay)
        exit(1)
    time.sleep(0.3)

protocol.opcode_logout(session)
session.close()
