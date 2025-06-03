#!/usr/bin/env python
# coding=utf-8
#
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.client import Endpoint

import json
import time
from itsi_kvstore import KVStoreHelper
import copy
from perf import Perf
import sys

"""
"""

my_logger = None

@Configuration()
class ConfITSICommand(StreamingCommand):
    """
    Command to update ITSI configuration via the REST API

    Example search to 
    | rest report_as=text /servicesNS/nobody/SA-ITOA/itoa_interface/service filter="{\"title\":{\"$regex\":\"^ABC.*App\"}}" fields="title,_key,description"
    | eval value=spath(value, "{}")
    | mvexpand value
    | eval title=spath(value, "title"), id=spath(value, "_key"), team=spath(value, "sec_grp"), description=spath(value, "description")
    | eval new_desc=printf("Updating desc for %s at %s", title, strftime(now(), "%F %T"))
    | json input=value indent=2 path=description remove="sec_grp,permissions,object_type" value=new_desc 
    | fields - splunk_server team id
    | stats values(value) as body
    | eval body=printf("[%s]", mvjoin(body, ","))
    | confitsi payload=body confirm=f


    Adaptive thresholds:

    kpis[{"_key": "<kpi id>", "adaptive_thresholds_is_enabled": <1=enabled, 0=disabled>,
                        "kpi_threshold_template_id" : <set to empty string ??> ]

    KPI Urgency

    Service Dependencies

    Set Team

    Set Description

    Set Title
    """

    opt_type = Option(
        doc='''
        **Syntax:** **type=***see itoa_interface/get_supported_object_types*
        **Description:** a valid object type to write based on get_supported_object_types
        **Default:** None''',
        name='type',
        require=True,
        validate=validators.Set("team", "entity", "service", "base_service_template", "kpi_base_search", "deep_dive", "glass_table", "home_view", 
        "kpi_template", "kpi_threshold_template", "event_management_state", "entity_relationship", "entity_relationship_rule", "entity_filter_rule", 
        "entity_type","entity_management_policies")
    ) 

    opt_is_partial = Option(
        doc='''
        **Syntax:** **is_partial=***boolean*
        **Description:** Sets the is_partial flag, set to True if the payload is partial
        **Default:** True''',
        name='is_partial',
        require=False,
        default=True,
        validate=validators.Boolean()) 

    opt_is_bulk = Option(
        doc='''
        **Syntax:** **is_bulk=***boolean*
        **Description:** runs a different endpoint that is not the bulk update endpoint, will be slower
        **Default:** True''',
        name='is_bulk',
        require=False,
        default=True,
        validate=validators.Boolean()) 

    # when updates are run through the object_type endpoint the _key is required, for create it is not allowed
    opt_is_update = Option(
        doc='''
        **Syntax:** **is_update=***boolean*
        **Description:**Is the request an update or create, applies only when is_bulk=False
        **Default:** False''',
        name='is_update',
        require=False,
        default=False,
        validate=validators.Boolean()) 

    opt_payload = Option(
        doc='''
        **Syntax:** **payload=***fieldname*
        **Description:** The name of the field in the record that contains payload for the call
        **Default:** payload    ''',
        name='payload',
        require=False,
        default="payload",
        validate=validators.Fieldname()
    )

    opt_confirm = Option(
        doc='''
        **Syntax:** **confirm=***boolean*
        **Description:** Dry run it if confirm=0
        **Default:** False''',
        name='confirm',
        require=False,
        default=False,
        validate=validators.Boolean()) 

    # region Command implementation
    def __init__(self):
        super(ConfITSICommand, self).__init__()


    def stream(self, records):
        kvstore = KVStoreHelper(self, object_type=self.opt_type)
        self.logger.info(f"Params confirm:{self.opt_confirm} is_partial:{self.opt_is_partial} object:{self.opt_type} payload:{self.opt_payload}")
        for r in records:
            try:
                body = json.loads(r[self.opt_payload])
            except json.JSONDecodeError as e:
                body = "Error parsing body: "+str(e)
                self.opt_confirm = False

            if not self.opt_confirm:
                yield {
                    "is_partial":self.opt_is_partial,
                    "object_type": self.opt_type,
                    "payload" : json.dumps(body)
                }
            else:
                try:
                    
                    if self.opt_is_bulk:
                        yield {**kvstore.write_bulk(body), **{"input":body}}
                    else:
                        ''' 
                        for create we use itoa_interface/object_type, if key is passed we use it, if not the system creates one 
                        for update we use itoa_object_type/_key set, key must be passed or an error will be generated, when update is called with no key it will create
                        '''
                        key = None
                        if "_key" in body and self.opt_is_update:
                            key=body["_key"]
                        yield {**kvstore.write_object(key, body, self.opt_is_partial), **{"input":body}}
                except Exception as e:
                    yield {"body" : f"Update failed {e}", 
                           "status" : "failed", 
                           "input" : body}


class ConfITSICommandHelper(object):

    def __init__(self, command):
        self.logger = command.logger
        self.kvstore = KVStoreHelper(command)


    def read(self, record, fields):
        id=record.get("id")
        filter = record.get("filter")
        res = []
        if id is not None:
            res = self.read_by_id(id, fields)
        elif filter is not None:
            res = self.read_by_filter(filter, fields)
        else:
            raise ValueError("read function expects either id (ie _key) or filter (mongo) argument")
        for r in res:
            r.update(record)
            r["hello"] = "Cesar"
        return res            

    def read_by_id(self, id, fields=None):
        '''
        Gets the current settings for the service(s) assigned 
        Returns a list of events with an item for each service found, ie if the filter matches 10 services then 10 rows are returned
        If an id was used then its 1 or an error if the id was not valid.
        '''
        return self.kvstore.read_list(
            filter = self.kvstore.get_filter(field="_key", value=id),
            fields = fields
        )


    def read_by_filter(self, filter, fields=None):
        '''
        Read all services that match based on this filter
        '''
        return self.kvstore.read_list(filter=filter, fields=fields)


    def write(self, record):
        '''
        Update the team on the services suppied (by id or filter) using the id passed in the param team
        :param id is the guid of the service to be updated, this is used over filter if present
        :return row that has had a new field added with the result of the update
        '''
        id = record.get("id")
        filter = record.get("filter")
        team = record.get("team")
        cfg = {
            "sec_grp":team,
            "description":f"updated by set team 123"
        }
        if id is not None:
            record["setteam"] = self.kvstore.write_object(id, cfg)
        else:
            # update in bulk with a filter means read all the services we want to update
            # get their configs and write them to a list for bulk_update
            cfg = []
            for r in self.kvstore.read_list(filter=filter, fields=["_key","title"]):
                cfg.append({"_key":r["_key"], "title":r["title"], "team":team})
                self.logger.info("IN BULK UPDATE")
            self.logger.info("OUT BULK UPDATE ")    
            record["setteam"] = self.kvstore.write_bulk(cfg)
            self.logger.info("OUT BULK UPDATE 2")    

        self.logger.info("BULK UPDATE DONE")
        return [record]


    

if __name__ == '__main__':
    dispatch(ConfITSICommand, module_name=__name__)
