#!/usr/bin/env python
# coding=utf-8
#
from __future__ import absolute_import, division, print_function, unicode_literals

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib import client
import splunklib
import json
from splunklib.client import Endpoint

'''try:
    from utils import parse
except ImportError:
    raise Exception("Add the SDK repository to your PYTHONPATH to run the examples "
                    "(e.g., export PYTHONPATH=~/splunk-sdk-python.")
'''

def foo(**kwargs):
    print()
if __name__ == '__main__':
    pswd="payday$$" #"testing@splunk"
    user="admin"
    host="localhost"
    port=8089
    service = client.connect(username=user, password=pswd, host=host, port=port)
    cx = splunklib.binding.connect(username=user, password=pswd, host=host, port=port)
    #x = cx.get("/servicesNS/nobody/SA-ITOA/itoa_interface/entity", count=2, filter='{"title": {"$regex":"(2|4)$"}}')
    url = "/servicesNS/nobody/SA-ITOA/event_management_interface/vLatest"

    gid = "b9fc0591-9d3b-47c1-a237-01f42a830e89"
    pid = "9afff548-9c57-11eb-9979-acde48001122"

    endpoint = Endpoint(service, '/servicesNS/nobody/SA-ITOA/event_management_interface/vLatest')
    path = "notable_event_group/" + gid
    payload = json.dumps({'_key': gid,
                'status': 2,
                'severity': 4
        })
    r = endpoint.post(path_segment=path, is_partial=1, break_group_policy_id=pid, body=payload)
    print (r)
    #print("Delete Status {}".format(x['status']))

    '''    jj = json.loads(x['body'].read())
    for j in jj:
        print( j)
    print (len(jj))'''

    cx.logout()
