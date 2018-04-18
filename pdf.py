#!/usr/bin/env python3

import socks
import importlib
import yaml
import os
import platform
from datetime import datetime, timedelta
import requests
import json
import sqlite3

workdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(workdir, "config.yml"), 'r') as config_obj:
    config = yaml.load(config_obj)

sql_conn = sqlite3.connect(os.path.join(workdir, '.storage.db'))
sql_c = sql_conn.cursor()
sql_c.execute('''CREATE TABLE IF NOT EXISTS pdf (
                      timestamp INTEGER NOT NULL PRIMARY KEY,
                      service VARCHAR(10),
                      success INTEGER)''')
slack_message = {'attachments': []}
checks = set()
for s in config['services']:
    if 'pdf_timeout' in config['services'][s] and 'pdf_timeout' in config['services'][s]:
        checks.add(s)
for service in checks:
    pdf_timeout = timedelta(minutes=config['services'][service]['pdf_timeout'])
    catalog_check = sql_c.execute(
                    'SELECT 1 FROM pdf WHERE service=? AND success ISNULL',
                    (service, )).fetchall()
    if len(catalog_check) > 0:
        r = json.loads(requests.get(
            config['mailgun']['url'] + '/events',
            auth=("api", config['mailgun']['key']),
            timeout=5
        ).text)
        for item in r['items']:
            if (
                item['message']['headers']['subject'].startswith(
                    config['pop3']['search_tag']['subject'])
                and 'delivery-status' in item
            ):
                ts = int(item['message']['headers']['subject'].split(':')[1].strip())
                catalog_check = sql_c.execute(
                    'SELECT 1 FROM pdf WHERE service=? AND success ISNULL AND timestamp=?',
                    (service, ts)).fetchall()
                if len(catalog_check) > 0:
                    pdf_timestamp = datetime.fromtimestamp(ts)
                else:
                    # skip already processed messages
                    continue
                delivery_timestamp = datetime.utcfromtimestamp(item['timestamp'])
                if 'slack' not in config:
                    print("{}: {} ~ {}".format(
                          pdf_timestamp,
                          item['envelope']['targets'],
                          delivery_timestamp - pdf_timestamp))
                sql_c.execute('UPDATE pdf SET success=? WHERE service=? AND timestamp=?',
                              (
                                  (delivery_timestamp - pdf_timestamp).seconds,
                                  service,
                                  ts
                               )
                              )
                sql_conn.commit()
                if delivery_timestamp - pdf_timestamp > pdf_timeout:
                    slack_message['attachments'].append({
                        'color': '#ffff00',
                        'text': '{}: PDF {}'.format(item['envelope']['targets'],
                                                    delivery_timestamp - pdf_timestamp),
                        'author_name': platform.node(),
                        'title': 'PDF {} warning'.format(service),
                        'ts': item['timestamp']
                    })
                # else:
                #     slack_message['attachments'].append({
                #         'color': '#00ff00',
                #         'text': '{} ~ {}'.format(pdf_timestamp, delivery_timestamp - pdf_timestamp),
                #         'author_name': platform.node(),
                #         'title': 'PDF {}'.format(service),
                #         'ts': item['timestamp']
                #     })
        uncatched_rows = sql_c.execute(
            'SELECT timestamp FROM pdf WHERE service=? AND success ISNULL',
            (service, )).fetchall()
        catalog = {ts for ts, in uncatched_rows}
        for ts in catalog:
            pdf_timestamp = datetime.fromtimestamp(int(ts))
            if datetime.utcnow() - pdf_timestamp > pdf_timeout:
                sql_c.execute('UPDATE pdf SET success=? WHERE service=? AND timestamp=?',
                              (-1, service, ts))
                sql_conn.commit()
                slack_message['attachments'].append({
                    'color': '#ff0000',
                    'text': 'timeout',
                    'author_name': platform.node(),
                    'title': 'PDF {}'.format(service),
                    'ts': ts
                })
    else:
        print(config['services'][service])
        # loading requested protocol
        protocol = importlib.import_module(
            'protocol.v' + str(config['services'][service]['protocol']))
        session = socks.socksocket()
        session.set_proxy(socks.SOCKS4, config['services'][service]['host'], 443)
        session.settimeout(config['services'][service]['timeout'])
        session.connect(('127.0.0.1', config['services'][service]['port']))
        pdf_timestamp = int(datetime.utcnow().timestamp())
        protocol.opcode_init(
            session,
            config['services'][service]['protocol'],
            config['services'][service]['envid'],
            str(config['services'][service]['key']))
        protocol.opcode_login(
            session,
            config['services'][service]['user'],
            config['services'][service]['password'])
        protocol.opcode_pdf_pinger(
            session,
            config['services'][service]['pdf_recipients'],
            pdf_timestamp)
        sql_c.execute(
            'INSERT INTO pdf(timestamp, service) VALUES (?, ?)', (pdf_timestamp, service))
        sql_conn.commit()
        protocol.opcode_logout(session)
        session.close()
sql_conn.close()
if 'slack' in config and len(slack_message['attachments']) > 0:
    requests.post(
        config['slack'],
        headers={'Content-type': 'application/json'},
        data=json.dumps(slack_message),
        timeout=5)
