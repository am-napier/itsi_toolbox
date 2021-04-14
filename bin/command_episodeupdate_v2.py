#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.client import Endpoint

import json
import time


@Configuration()
class UpdateEpisodeCommand(StreamingCommand):
    """
        Update episodes using event properties
    """

    # region Command implementation
    def __init__(self):
        super(UpdateEpisodeCommand, self).__init__()

    def prepare(self):
        self.endpoint = Endpoint(self.service, '/servicesNS/nobody/SA-ITOA/event_management_interface/vLatest')

    def stream(self, records):
        """
        Process all events.
        :param records: An iterable stream of events from the command pipeline.
        :return: `None`.
        """
        self.logger.info('Entering stream.')
        t1 = time.time()
        # Put your event transformation code here
        for record in records:
            self.logger.info('Record {0}'.format(record))
            t2 = time.time()
            group_id = record.get('itsi_group_id')
            policy_id = record.get('itsi_policy_id')
            severity = record.get('severity')
            status = record.get('status')
            brk = record.get('break', "n").lower()
            self.logger.info("break ERING {} ".format(brk))
            break_episode = brk.startswith("1") or brk.startswith("t") or brk.startswith("y")

            self.logger.info("break ERING {} ".format(break_episode))

            payload = {'_key': group_id}
            if status:
                payload['status'] = status
            if severity:
                payload['severity'] = severity
            query = {"body": json.dumps(payload),
                      "is_partial": 1, "owner":"n/a", "title": "n/a", "description": "n/a"}
            if break_episode:
                query["break_group_policy_id"] = policy_id
                self.logger.info('BreAking Epsiode')
            self.logger.info('Payload={}'.format(query))
            r = None
            try:
                self.logger.info("before")
                response = self.endpoint.post(path_segment="notable_event_group/"+group_id, **query)
                self.logger.info("after {}".format(response))
                if response:
                    self.logger.info('Sent POST request to update episode itsi_group_id="{}" status={}'.format(
                                    json.loads(response['body'].read())['_key'], response['status']))
                    record["update-status"] = response['status']

            except Exception as e:
                self.logger.error('Caught exception: {}'.format(e))
            t3 = time.time()
            self.logger.info("Update Time is:{}".format(t3 - t2))
            yield record

        self.logger.info("Full update time is:{}".format(time.time() - t1))

    # endregion


if __name__ == '__main__':
    dispatch(UpdateEpisodeCommand, module_name=__name__)