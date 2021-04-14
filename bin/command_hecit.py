#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import requests

import json
import time
import uuid


@Configuration()
class BlaggertCommand(StreamingCommand):


    opt_token = Option(
        doc='''
        **Syntax:** **token=***<fieldname>*
        **Description:** HEC token to use.
        **Default:** None''',
        name='token',
        require=True,
        validate=validators.Fieldname())

    opt_server = Option(
        doc='''
        **Syntax:** **server=***<fieldname>*
        **Description:** Server to send the payload to.
        **Default:** localhost''',
        name='server',
        require=False,
        default='localhost',
        validate=validators.Fieldname())

    opt_port = Option(
        doc='''
        **Syntax:** **port=***<fieldname>*
        **Description:** HEC Port, not fortified red wine.
        **Default:** 8088''',
        name='port',
        require=False,
        default=8088,
        validate=validators.Integer())

    def __init__(self):
        super(BlaggertCommand, self).__init__()

    def prepare(self):
        return

    def stream(self, records):

        # Put your event transformation code here
        url = "https://{}:{}/services/collector/event".format(self.opt_server, self.opt_port)
        headers = {
            "Authorization": "Splunk {}".format(self.opt_token)
        }
        for record in records:
            self.logger.info('Record {0}'.format(record))
            t2 = time.time()

            payload = {
                "event" : {
                    "event_id" : str(uuid.uuid4())
                }
            }
            for k, v in record.iteritems():
                payload["event"][k] = v

            payload_str = json.dumps(payload)
            self.logger.info('send to HEC url={} - payload='.format(url, payload_str))
            try:
                res = requests.post(url, data=payload_str, headers=headers, verify=False)
                res.raise_for_status()
                self.logger.info("Sweet as {} {}".format(res.status_code, res.text))
                record["blaggert_says"] = "Done it"
            except Exception as e:
                self.logger.error('Send HEC Caught exception: {}'.format(e))
                record["blaggert_says"] = "Buggered it {}".format(e)

            yield record


if __name__ == '__main__':
    dispatch(BlaggertCommand, module_name=__name__)