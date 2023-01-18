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
        self.endpoint = Endpoint(self.service, '/servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_group')
        

    def stream(self, records):
        """
        Process all events.
        :param records: An iterable stream of events from the command pipeline.
        :return: `None`.

        curl -k -u admin:r3knulp5 https://localhost:8089/servicesNS/nobody/SA-ITOA/event_management_interface
        /notable_event_group    
        -X POST -H "Content-Type:application/json" 
        -d '{"data":{"status":"1","severity":"4","_key":"004b2eed-4551-481f-9487-9cf96b58e59d"}}'

        curl -k -u admin:r3knulp5 https://localhost:8089/servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_group/id/?is_partial_data=1 
        -X POST -H "Content-Type:application/json" 
        -d '{"severity": "6"}' 


        http://aws:8000/en-GB/splunkd/__raw/servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_group?break_multiple_groups=true&output_mode=json

        {"data":[
          {"status":"5","event_identifier_hash":"b128a722-cc5b-4506-8949-57a83a67fdaa","_key":"b128a722-cc5b-4506-8949-57a83a67fdaa","itsi_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a","break_group_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a",
                "title":"Episode Key: id-7 - 05:52:00 000000","description":"Episode Key: id-7 - 05:52:00 000000","severity":"1","owner":"admin"},
          {"status":"5","event_identifier_hash":"008d5d18-04fc-4204-beb7-b9f958370ae6","_key":"008d5d18-04fc-4204-beb7-b9f958370ae6","itsi_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a","break_group_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a",
                "title":"Episode Key: id-8 - 05:52:00 000000","description":"Episode Key: id-8 - 05:52:00 000000","severity":"1","owner":"admin"},
          {"status":"5","event_identifier_hash":"7becd9ea-a4e2-44fb-b1d2-201f8df8971a","_key":"7becd9ea-a4e2-44fb-b1d2-201f8df8971a","itsi_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a","break_group_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a",
                "title":"Episode Key: id-9 - 05:52:00 000000","description":"Episode Key: id-9 - 05:52:00 000000","severity":"1","owner":"admin"},
          {"status":"5","event_identifier_hash":"de5f60bd-a64e-48f0-b7f7-833042b82d0f","_key":"de5f60bd-a64e-48f0-b7f7-833042b82d0f","itsi_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a","break_group_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a",
                "title":"Episode Key: id-10 - 05:52:00 000000","description":"Episode Key: id-10 - 05:52:00 000000","severity":"1","owner":"admin"}
        ],"earliest_time":"-12h@h","latest_time":"now"}

        Single Event Changed
        http://aws:8000/en-GB/splunkd/__raw/
        servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_group/100ec911-bf1c-4ab6-be27-540199a35931?output_mode=json
        servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_group
        {"_key":"100ec911-bf1c-4ab6-be27-540199a35931","status":"2","itsi_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a"}
        FIELDS:
            _key
            status
            itsi_policy_id

        Single Event Broken
        http://aws:8000/en-GB/splunkd/__raw/servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_group?break_group_policy_id=449339e6-1f0e-11ed-98ee-0291d3a1879a
        {"_key":"fd6ee035-a600-4723-8982-6ea6462dd7fa","status":"5","title":"Episode Key: id-4 - 05:51:00 000000","description":"Episode Key: id-4 - 05:51:00 000000","severity":1,"owner":"admin","itsi_policy_id":"449339e6-1f0e-11ed-98ee-0291d3a1879a"}
        FIELDS: 
            _key
            status
            title
            description
            severity
            owner
            itsi_policy_id

        """
        def label(lbl, str):
            return lbl if str is None else ""

        def usage_ids(rec, gid, pid):
            rec['episodeupdate-usage'] = "Updates require these missing fields {}{}".format(
                label("itsi_group_id", gid), label(", itsi_policy_id", pid))

        def usage_breaking(rec, owner, title, description, severity, status):
            rec['episodeupdate-usage'] = "Breaking requires these missing fields: {}{}{}{}{}".format(
                label("owner", owner), label(", title", title), label(", description", description), 
                label(", severity", severity), label(", status", status))

        self.logger.info('Entering stream.')
        t1 = time.time()
        # Put your event transformation code here
        for record in records:
            self.logger.info('Record {0}'.format(record))
            t2 = time.time()

            # these are required to be passed in the payload
            group_id = record.get('itsi_group_id')
            policy_id = record.get('itsi_policy_id')

            if not group_id or not policy_id:
                usage_ids(record, group_id, policy_id)
                yield record
                continue

            self.logger.info(f"Passed 1 G={group_id}  P={policy_id}")

            # these can be changed by the user
            severity = record.get('severity')
            status = record.get('status')
            owner = record.get('owner')

            # required when breaking epsiodes but user cannot change these
            title = record.get('title')
            description = record.get('description')

            brk = record.get('break', "n").lower()
            break_episode = status=="5" or brk.startswith("1") or brk.startswith("t") or brk.startswith("y")
            if break_episode and None in (owner, title, description, severity, status):
                usage_breaking(record, owner, title, description, severity, status)
                yield record
                continue

            payload = {'_key': group_id}
            if status:
                payload['status'] = status
            if severity:
                payload['severity'] = severity
            if owner:
                payload['owner'] = owner
            if title:
                payload['title'] = title
            if description:
                payload['description'] = description
            query = {"body": json.dumps(payload),
                      "is_partial": 1} 
            if break_episode:
                query["break_group_policy_id"] = policy_id
                self.logger.info('BreAking Epsiode')
            self.logger.info('Payload={}'.format(query))
            
            try:
                response = self.endpoint.post(path_segment=group_id, **query)
                self.logger.info("after {}".format(response))
                if response:
                    self.logger.info('Sent POST request to update episode itsi_group_id="{}" status={}'.format(
                                    json.loads(response['body'].read())['_key'], response['status']))
                    record["update-status"] = response['status']
                    if int(response['status']) > 299:
                        self.logger.error("POST failed, check logs ")
                        record["update-status"] = response['status']
                else:
                    # should be dead code
                    self.logger.error("POST failed, No response sent")
                    record["update-status"] = "POST Failed, check splunkd.log"
                    record["update-payload"] = query 
            except Exception as e:
                self.logger.error('Caught exception: {}'.format(e))
                record["update-status"] = f"POST Failed, Error: {e}"
                record["update-payload"] = query 
            t3 = time.time()
            record["update-time"] = t3 - t2
            self.logger.info("Update Time is:{}".format(t3 - t2))
            yield record

        self.logger.info("Full update time is:{}".format(time.time() - t1))

    # endregion


if __name__ == '__main__':
    dispatch(UpdateEpisodeCommand, module_name=__name__)