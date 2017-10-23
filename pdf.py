#!/usr/bin/env python3

import socks
from argparse import ArgumentParser
import importlib
import yaml
import os
import platform
from datetime import datetime, timedelta
import requests
import json

workdir = os.path.dirname(os.path.realpath(__file__))
catalog_path = os.path.join(workdir, 'pdf_catalog')

catalog = set()
if os.path.isfile(catalog_path):
    with open(catalog_path, 'rt') as catalog_obj:
        for line in catalog_obj:
            catalog.add(line.strip())

with open(os.path.join(workdir, "config.yml"), 'r') as config_obj:
    config = yaml.load(config_obj)

# Preparing arguments
argparser = ArgumentParser(description='Check PDF health')
argparser.add_argument('--service', help='service name', choices=[str(s) for s in config['services']], required=True)
argparser.add_argument('--send', help='send PDF sample', action="store_true")
argparser.add_argument('--pop3', help='check pop3 mailbox', action="store_true")
argparser.add_argument('--mailgun', help='check mailgun API', action="store_true")
argparser.add_argument('--slack', help='send slack notifications', action="store_true")
args = argparser.parse_args()

if args.send:
    print(config['services'][args.service])
    # loading requested protocol
    protocol = importlib.import_module('protocol.v' + str(config['services'][args.service]['protocol']))

    session = socks.socksocket()
    session.set_proxy(socks.SOCKS4, config['services'][args.service]['host'], 443)
    session.settimeout(config['services'][args.service]['timeout'])
    session.connect(('127.0.0.1', config['services'][args.service]['port']))
    pdf_timestamp = int(datetime.utcnow().timestamp())
    protocol.opcode_init(
        session,
        config['services'][args.service]['protocol'],
        config['services'][args.service]['envid'],
        str(config['services'][args.service]['key']))
    protocol.opcode_login(
        session,
        config['services'][args.service]['user'],
        config['services'][args.service]['password'])
    protocol.opcode_pdf_pinger(
        session,
        config['services'][args.service]['pdf_recipients'],
        pdf_timestamp)
    catalog.add(pdf_timestamp)
    with open(catalog_path, 'wt') as catalog_obj:
        for ts in catalog:
            catalog_obj.write(str(ts) + '\n')
    protocol.opcode_logout(session)
    session.close()
elif args.pop3:
    import poplib

    pop_client = poplib.POP3_SSL(config['pop3']['server'], port=config['pop3']['port'])
    pop_client.set_debuglevel(0)
    pop_client.getwelcome()
    pop_client.user(config['pop3']['login'])
    pop_client.pass_(config['pop3']['password'])
    messages_list = pop_client.list()[1]
    for m in messages_list:
        m_headers = list()
        # remove newlines from message headers
        for h in pop_client.top(int(m.split()[0]), 0)[1]:
            header_string = h.decode('UTF-8')
            if header_string.startswith(' ') or header_string.startswith('\t'):
                m_headers[len(m_headers) - 1] = m_headers[len(m_headers) - 1] + ' ' + header_string.strip()
            else:
                m_headers.append(header_string)
        # looking for required headers
        r_subject = r_time = None
        for h in m_headers:
            if h.startswith('Subject:'):
                subject = h.replace('Subject:', '').strip()
                if config['pop3']['search_tag']['subject'] in subject:
                    r_subject = h.replace('Subject:', '').strip()
                break
        if r_subject is not None:
            for h in m_headers:
                if h.startswith('Received:') and config['pop3']['search_tag']['r_time'] in h:
                    r_time = datetime.strptime(h.split(';')[-1].strip(), '%a, %d %b %Y %H:%M:%S %z')
                    break
            print("%s: %s" % (str(r_time), subject))
elif args.mailgun:
    r = json.loads(requests.get(
        config['mailgun']['url'] + '/events',
        auth=("api", config['mailgun']['key']),
    ).text)
    result = list()
    result_d = dict()
    timeouts = list()
    for item in r['items']:
        if (
                item['message']['headers']['subject'].startswith(config['pop3']['search_tag']['subject'])
            and 'delivery-status' in item
        ):
            if item['message']['headers']['subject'].split(':')[1].strip() in catalog:
                pdf_timestamp = datetime.fromtimestamp(
                    int(item['message']['headers']['subject'].split(':')[1])
                )
            else:
                # skip already processed messages
                continue
            delivery_timestamp = datetime.utcfromtimestamp(item['timestamp'])
            if pdf_timestamp not in result_d:
                result_d.update({pdf_timestamp: {
                    'target': item['envelope']['targets'],
                    'delta': delivery_timestamp - pdf_timestamp,
                    'delivered': delivery_timestamp.strftime('%Y %b %d %H:%M:%S')
                }})
            result.append("%s: %s ~ %s" %
                          (pdf_timestamp, item['envelope']['targets'], delivery_timestamp - pdf_timestamp))
            catalog.remove(item['message']['headers']['subject'].split(':')[1].strip())
    for ts in catalog:
        pdf_timestamp = datetime.fromtimestamp(
            int(item['message']['headers']['subject'].split(':')[1])
        )
        if delivery_timestamp - pdf_timestamp > timedelta(minutes=config['services'][args.service]['pdf_timeout']):
            timeouts.append(pdf_timestamp)
            catalog.remove(item['message']['headers']['subject'].split(':')[1].strip())
    # saving catalog state
    with open(catalog_path, 'wt') as catalog_obj:
        for ts in catalog:
            catalog_obj.write(str(ts) + '\n')
    if args.slack:
        if 'timestamp' not in config:
            timestamp_format = '%H:%M UTC'
        else:
            timestamp_format = config['timestamp']
        if 'nodename' not in config:
            nodename = platform.node()
        else:
            nodename = config['nodename']
        for item in result_d:
            if result_d[item]['delta'] > timedelta(minutes=config['services'][args.service]['pdf_timeout']):
                slack_message = '<!here> at %s ``` %s: PDF %s - warning ```' % \
                                (result_d[item]['delivered'], result_d[item]['target'], result_d[item]['delta'])
            else:
                slack_message = "[%s] %s: to <%s> at %s PDF ~ %s - OK" % \
                                (datetime.utcnow().strftime(timestamp_format),
                                 args.service,
                                 result_d[item]['target'],
                                 result_d[item]['delivered'],
                                 result_d[item]['delta'])
            requests.post(
                config['slack'],
                headers={'Content-type': 'application/json'},
                data=json.dumps({'text': slack_message})
            )
        for w in timeouts:
            requests.post(
                config['slack'],
                headers={'Content-type': 'application/json'},
                data=json.dumps({'text': '<!here> TIMEOUT ' + w})
            )
    else:
        print('\n'.join(result))
