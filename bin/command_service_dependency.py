#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.client import Endpoint

import json
import time
from itsi_kvstore import KVStoreHelper
import copy
from perf import Perf

#DEF_FIELDS = "time_variate_thresholds,adaptive_thresholds_is_enabled,adaptive_thresholding_training_window," \
#             "kpi_threshold_template_id,tz_offset"


def get_bool(b):
    return str(b).lower in ["true", "t", 1, "yes", "ok", "indeed-illy do!"]


@Configuration()
class ServiceDependencyCommand(StreamingCommand):
    """
    eval parent_id=xxx, child_id=yyy kpi_id=zzz urgency=7 | servicedependency mode=add
    """

    opt_mode = Option(
        doc='''
        **Syntax:** **mode=***string*
        **Description:** one of add or remove
        **Default:** add''',
        name='mode',
        require=True,
        default="add")

    def_urgency = Option(
        doc='''
        **Syntax:** **default_urgency=***int*
        **Description:** value between 0 and 11
        **Default:** 5''',
        name='default_urgency',
        require=False,
        default=5,
        validate=validators.Integer())

    # region Command implementation
    def __init__(self):
        super(ServiceDependencyCommand, self).__init__()


    def prepare(self):
        pass

    def stream(self, records):
        """
        Process all events.
        :param records: An iterable stream of events from the command pipeline.
        :return: `None`.

        add/update : parent=xxx, child=yyy, kpiid=zzz, urgency=0-11 | servicedependency mode=add
        remove: parent=xxx, child=yyy, kpiid=zzz  | servicedependency mode=remove
        """
        self.logger.info('Service Dependency Command entering stream.')
        t1 = time.time()
        mode = self.opt_mode.lower()

        if not mode in ['add', "remove"]:
            self.logger.error("unsupported mode, only add or remove are supported")
            return

        # Put your event transformation code here
        helper = ServiceDependencyHelper(self)
        for record in records:
            # delete this before production
            self.logger.info('Stream Record {0}'.format(record))
            t2 = time.time()

            if mode == 'add':
                helper.do_add(record)
            else:
                helper.do_remove(record)

            self.logger.info("{} complete in {} secs".format(mode, time.time() - t2))
            yield record

        self.logger.info("Full update time is:{}".format(time.time() - t1))

    # endregion


class ServiceDependencyHelper(object):

    def __init__(self, command):
        self.logger = command.logger
        self.def_urgency = command.def_urgency
        self.kvstore = KVStoreHelper(command)
        self.PARENT_LINKS = "services_depends_on"
        self.CHILD_LINKS = "services_depending_on_me"
        self.KPI_LIST = "kpis_depending_on"
        self.URGENCY_LIST = "overloaded_urgencies"


    def insert_or_update_links(self, object, tag, svc_id, kpi_id, urgency=None):
        """
        This method is inserting or updating the required bits of the link config in object
        Similar link config is used in the parent and the child, the main difference is the parent
        might have overloaded_urgencies object if the defaults are not used.
        Defaults are 5 for KPIs and 11 for health scores

        Params:
            object (dict) is a service config
            tag (string) is the name of the link config object being updated.  Value is:
                services_depends_on - if object is the parent end of the link
                services_depending_on_me - if object is the child end of the link
            svc_id (string) is the service being linked to
            kpi_id (string) is the id of the kpi in the service being linked to
            urgency (int) is value to insert in overloaded_urgencies (if provided)
        returns:
            the new or modified link object

        Object structures look like this:
            from the parent point down at the child
                 "services_depends_on" : [
                    {
                        "serviceid":svc_id
                        "kpis_depending_on":[kpi_id, ...]
                        "overloaded_urgencies": {id:int, ...}
                    }
                ]
            from the child pointing at the parent
                 "services_depending_on_me" : [
                    {
                        "servcieid": svc_id,
                        "kpis_depending_on": [kpi_id, ...]
                    }
                 ]
        """

        # first create the array called tag in object if it doesn't exist, I've seen this in some cases
        if not tag in object:
            object[tag] = []
        # create a default link object
        default_link = {"serviceid": svc_id, self.KPI_LIST: []}
        # next get the link object from object for svc_id, or use the default
        link = next((item for item in object[tag] if item['serviceid'] == svc_id), default_link)
        # add it to the array if its not there
        if link not in object[tag]:
            object[tag].append(link)
        """add the kpi to the links object if its not there"""
        if kpi_id not in link[self.KPI_LIST]:
            link[self.KPI_LIST].append(kpi_id)
        """update urgency if provided, should only happen for the parent node"""
        if urgency is not None:
            if not self.URGENCY_LIST in link:
                link[self.URGENCY_LIST] = {}
            link[self.URGENCY_LIST][kpi_id] = urgency
        # return is for testing only
        return link

    def do_add(self, record, dry_run=False):
        """

        """
        parent_id = record.get("parent", None)
        child_id = record.get("child", None)
        kpi_id = record.get('kpiid', None)
        if None in [parent_id, child_id, kpi_id]:
            raise RuntimeError("Missing required fields parent:{}, child:{}, kpi:{}".format(parent_id, child_id, kpi_id))
        parent = self.kvstore.read_object(parent_id)
        child = self.kvstore.read_object(child_id)
        urgency = record.get('urgency', self.def_urgency)

        self.logger.info("DO ADD: parent:{}, child:{}, kpi:{} urgency:{}".format(parent_id, child_id, kpi_id, urgency))
        parent_links = self.insert_or_update_links(parent, self.PARENT_LINKS, child_id, kpi_id, urgency)
        child_links = self.insert_or_update_links(child, self.CHILD_LINKS, parent_id, kpi_id)
        self.logger.info("Linking parent {} to child {} with parent-cfg:{} child-cfg:{}".format(parent_id, child_id,
                                json.dumps(parent_links, indent=2), json.dumps(child_links, indent=2)))
        payload = [
            {
                "_key" : parent_id,
                "object_type":"service",
                "title" : parent["title"],
                self.PARENT_LINKS: parent[self.PARENT_LINKS]
            },
            {
                "_key": child_id,
                "object_type": "service",
                "title": child["title"],
                self.CHILD_LINKS: child[self.CHILD_LINKS]
            }
        ]
        if not dry_run:
            resp = self.kvstore.write_bulk(json.dumps(payload))

        return payload
        # write the new services

    def remove_links(self, links, svc_id, kpi_id):
        """
        object is an array of dict one per service.
            [
                {
                    "serviceid":svc_id
                    "kpis_depending_on":[kpi_id, ...]
                    "overloaded_urgencies": {id:int, ...} # optional, might not be there
                },
                { ... }
            ]
        """
        # find the one for svc_id
        svc_link = next((link for link in links if link['serviceid'] == svc_id and kpi_id in link[self.KPI_LIST]), None)
        try:
            svc_link[self.KPI_LIST].remove(kpi_id)
            if self.URGENCY_LIST in svc_link:
                svc_link[self.URGENCY_LIST].pop(kpi_id, None)
            # if this was the only item in the list remove the link object
            if len(svc_link[self.KPI_LIST])==0:
                links.remove(svc_link)
        except Exception as e:
            self.logger.warn("Error in remove links, please forgive crappy message... {} ".format(e))
            """fail the update because we can't complete with a partial set"""
            raise e

    def do_remove(self, record, dry_run=False):
        """
        This method is removing the link between two services
        See do_add for example structures

        Params:
            record (dict) is a map of values from the row in the search bar
        returns:
            ??
        """
        parent_id = record.get("parent", None)
        child_id = record.get("child", None)
        kpi_id = record.get('kpiid', None)
        if None in [parent_id, child_id, kpi_id]:
            raise RuntimeError(
                "Missing required fields parent:{}, child:{}, kpi:{}".format(parent_id, child_id, kpi_id))
        parent = self.kvstore.read_object(parent_id)
        child = self.kvstore.read_object(child_id)
        self.logger.info("DO REMOVE: parent:{}, child:{}, kpi:{} ".format(parent_id, child_id, kpi_id))
        self.remove_links(parent[self.PARENT_LINKS], child_id, kpi_id)
        self.remove_links(child[self.CHILD_LINKS], parent_id, kpi_id)

        payload = [
            {
                "_key": parent_id,
                "object_type": "service",
                "title": parent["title"],
                self.PARENT_LINKS: parent[self.PARENT_LINKS]
            },
            {
                "_key": child_id,
                "object_type": "service",
                "title": child["title"],
                self.CHILD_LINKS: child[self.CHILD_LINKS]
            }
        ]
        if not dry_run:
            resp = self.kvstore.write_bulk(json.dumps(payload))

        return payload

if __name__ == '__main__':
    dispatch(ServiceDependencyCommand, module_name=__name__)
