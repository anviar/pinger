#!/usr/bin/env python3

import os
import smtplib
import subprocess
import yaml
from email.mime.text import MIMEText

workdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(workdir, "config.yml"), 'r') as config_obj:
    config = yaml.load(config_obj)

for service in config['services']:
    command=[os.path.join(workdir,"pinger.py")]
    for key, value in config['services'][service].items():
        command.append('--' + key)
        command.append(str(value))
    dnp_ping = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if dnp_ping.returncode !=0:
        for recepient in config['smtp']['to']:
            msg = MIMEText(dnp_ping.stdout.decode("UTF-8"))
            msg['Subject'] = config['smtp']['subject'] + ' ' + str(service)
            msg['From']    = config['smtp']['from']
            msg['To']      = recepient
            s = smtplib.SMTP(config['smtp']['host'], config['smtp']['port'])
            s.login(config['smtp']['login'], config['smtp']['password'])
            s.sendmail(msg['From'], msg['To'], msg.as_string())
            s.quit()