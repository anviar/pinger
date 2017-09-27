#!/usr/bin/env python3

import socks
from argparse import ArgumentParser
import importlib
import yaml
import os

workdir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(workdir, "config.yml"), 'r') as config_obj:
    config = yaml.load(config_obj)

# Preparing arguments
argparser = ArgumentParser(description='Check PDF health')
argparser.add_argument('--service', help='service name', choices=[str(s) for s in config['services']], required=True)
argparser.add_argument('--send', help='send PDF sample', action="store_true")
argparser.add_argument('--pop3', help='check pop3 mailbox', action="store_true")
argparser.add_argument('--mailgun', help='check mailgun API', action="store_true")
args = argparser.parse_args()

if args.send:
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
    protocol.opcode_pdf_pinger(
        session,
        config['services'][args.service]['pdf_recipients'])

    protocol.opcode_logout(session)
    session.close()
elif args.pop3:
    import poplib
    from datetime import datetime

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
    import requests
    import json
    from datetime import datetime

    r = json.loads(requests.get(
        config['mailgun']['url'] + '/events',
        auth=("api", config['mailgun']['key']),
    ).text)
    for item in r['items']:
        if (
                item['message']['headers']['subject'].startswith(config['pop3']['search_tag']['subject'])
            and 'delivery-status' in item
        ):
            pdf_timestamp = datetime.fromtimestamp(
                int(item['message']['headers']['subject'].split(':')[1]) // 1000
            )
            delivery_timestamp = datetime.fromtimestamp(item['timestamp'])
            print("%s: %s ~ %s" % (pdf_timestamp, item['envelope']['targets'], delivery_timestamp - pdf_timestamp))
