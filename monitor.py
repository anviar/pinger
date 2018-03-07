#!/usr/bin/env python3

import os
import smtplib
import subprocess
import yaml
from email.mime.text import MIMEText
from argparse import ArgumentParser
import requests
import json
import platform
import sys
import sqlite3
import time

# Preparing arguments
argparser = ArgumentParser(description='Check configured services health')
argparser.add_argument('--mail', help='send mail notifications', action="store_true")
argparser.add_argument('--slack', help='send slack notifications', action="store_true")
args = argparser.parse_args()

workdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(workdir, "config.yml"), 'r') as config_obj:
    config = yaml.load(config_obj)

if 'nodename' not in config:
    nodename = platform.node()
else:
    nodename = config['nodename']

if 'timestamp' not in config:
    timestamp_format = '%H:%M UTC'
else:
    timestamp_format = config['timestamp']

sql_conn = sqlite3.connect(os.path.join(workdir, '.storage.db'))
sql_c = sql_conn.cursor()
sql_c.execute('''CREATE TABLE IF NOT EXISTS history (
                      timestamp INTEGER NOT NULL PRIMARY KEY,
                      service VARCHAR(10),
                      code INTEGER,
                      std TEXT)''')

for service in config['services']:
    command = [sys.executable, os.path.join(workdir, "pinger.py"), '--service', service]
    dnp_ping = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sql_c.execute('INSERT INTO history VALUES (?, ?, ?, ?)',
                  (
                        int(time.time()),
                        service,
                        dnp_ping.returncode,
                        dnp_ping.stdout.decode("UTF-8"))
                  )
    sql_conn.commit()
    if dnp_ping.returncode != 0:
        if args.mail:
            for recepient in config['smtp']['to']:
                msg = MIMEText(dnp_ping.stdout.decode("UTF-8"))
                msg['Subject'] = config['smtp']['subject'] + ' ' + str(service)
                msg['From'] = config['smtp']['from']
                msg['To'] = recepient
                s = smtplib.SMTP(config['smtp']['host'], config['smtp']['port'])
                s.login(config['smtp']['login'], config['smtp']['password'])
                s.sendmail(msg['From'], msg['To'], msg.as_string())
                s.quit()
        if args.slack:
            slack_message = '<!here> {} ```{}```'.format(
                platform.node(), dnp_ping.stdout.decode("UTF-8"))
            requests.post(
                config['slack'],
                headers={'Content-type': 'application/json'},
                data=json.dumps({'text': slack_message}),
                timeout=5
            )
sql_conn.close()
