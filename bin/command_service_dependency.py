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

#DEF_FIELDS = "time_variate_thresholds,adaptive_thresholds_is_enabled,adaptive_thresholding_training_window," \
#             "kpi_threshold_template_id,tz_offset"

"""
Useful testing searches

# find and display all the dependency links for the services being linked/unlinked

| rest report_as=text /servicesNS/nobody/SA-ITOA/itoa_interface/service/ fields="services_depends_on,services_depending_on_me,title"
| eval svc=spath(value, "{}")
| mvexpand svc
| fields - value
| eval children="[".mvjoin(spath(svc, "services_depends_on{}"), ",")."]", parents="[".mvjoin(spath(svc, "services_depending_on_me{}"), ",")."]", title=spath(svc, "title")
| search title IN (A_Tes*)
| prettyprint fields="children,parents"
| fields title, parents, children, svcx

``` 
 add service dependencies for named KPIs (custom_1,custom_2) AND SHS via appendpipe
 note the streamstats hack to set urgency to a max of 11
 swap mode=add to mode=remove to clear them out again
```
| makeresults 
| eval parent_name="A_Test_One", child_name=split("A_Test_Two,A_Test_Three,A_Test_Four", ","), kpi_name=split("custom_1,custom_2",",")
| mvexpand child_name
| mvexpand kpi_name
``` get the child IDs```
| join child_name,kpi_name [|`service_kpi_list` | rename service_name as child_name, serviceid as child ]
``` get the parent IDs ```
| lookup service_kpi_lookup title as parent_name OUTPUT _key as parent
``` add SHS too```
| appendpipe [| dedup parent, child | fields - kpiid]
| streamstats window=11 count as urgency
| servicedependency mode="add"

"""

def get_bool(b):
    return str(b).lower in ["true", "t", 1, "yes", "ok", "indeed-illy do!"]


@Configuration()
class ServiceDependencyCommand(StreamingCommand):
    """
    eval parent=xxx, child=yyy kpiid=zzz urgency=7 | servicedependency mode=add
    """

    opt_mode = Option(
        doc='''
        **Syntax:** **mode=***string*
        **Description:** one of add or remove
        **Default:** add''',
        name='mode',
        require=True,
        default="add",
        validate=validators.Set("add", "remove"))

    opt_is_debug = Option(
        doc='''
        **Syntax:** **debug=***boolean*
        **Description:** Don't do anything but validate the call
        **Default:** False''',
        name='debug',
        require=False,
        default=False,
        validate=validators.Boolean())

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

        # Put your event transformation code here
        helper = ServiceDependencyHelper(self)
        try:
            for record in records:
                if self.opt_mode == 'add':
                    helper.do_add(record)
                else:
                    helper.do_remove(record)

            yield {
                'payload' : helper.get_payload()
            }
        
            self.logger.info("Total time is:{}".format(time.time() - t1))
        except Exception as e:
            msg = "Error, check KPI is a valid dependency, message was: %s " % str(e)
            yield {
                "ErrorMessage": msg
            }
            self.logger.error(msg)


class ServiceDependencyHelper(object):

    def __init__(self, command):
        self.logger = command.logger
        self.def_urgency = command.def_urgency
        self.kvstore = KVStoreHelper(command)
        self.PARENT_LINKS = "services_depends_on"
        self.CHILD_LINKS = "services_depending_on_me"
        self.KPI_LIST = "kpis_depending_on"
        self.URGENCY_LIST = "overloaded_urgencies"
        # this services map is a cache for all service config during the execution of this command
        self.services = {}


    def get_payload(self):
        return json.dumps(list(self.services.values()))


    def get_service(self, id):
        """
        Read the service from the kvstore or from the local cache
        If it's not found make a dummy place holder that can be seen in the output
        """
        if id not in self.services.keys():
            try:
                cfg = self.kvstore.read_object(id)
                self.services[id] = {
                    "_key" : id,
                    "title" : cfg["title"]}
                if self.PARENT_LINKS in cfg:    
                    self.services[id][self.PARENT_LINKS] = cfg[self.PARENT_LINKS]
                if self.CHILD_LINKS in cfg:    
                    self.services[id][self.CHILD_LINKS] = cfg[self.CHILD_LINKS]
            except Exception as e:
                # service doesn't exist, dummy needs some empty arrays so we don't throw exceptions
                self.logger.error(f"Service Read Failure for {id} : {e}")
                self.services[id] = {
                    "MISSING_key" : id,
                    "ERROR" : str(e),
                    #self.KPI_LIST : [],
                    self.PARENT_LINKS :[],
                    self.CHILD_LINKS :[]
                }
        return self.services[id]


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
        # add the kpi to the links object if its not there
        if kpi_id not in link[self.KPI_LIST]:
            link[self.KPI_LIST].append(kpi_id)
        # update urgency if provided, should only happen for the parent node
        if urgency is not None:
            if not self.URGENCY_LIST in link:
                link[self.URGENCY_LIST] = {}
            link[self.URGENCY_LIST][kpi_id] = urgency
        # return is for testing only
        return link


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
        if svc_link is None:
            self.logger.warn(f"No kpi called {kpi_id} exists in svc {svc_id} for links {links}")
            return
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



    def do_add(self, record, dry_run=False):
        """
        """
        parent_id = record.get("parent", None)
        child_id = record.get("child", None)
        kpi_id = record.get('kpiid', "")
        if "" == kpi_id:
            kpi_id = "SHKPI-%s" % child_id
        if None in [parent_id, child_id, kpi_id]:
            raise RuntimeError("Missing required fields parent:{}, child:{}, optional (kpi:{})".format(parent_id, child_id, kpi_id))

        parent = self.get_service(parent_id)
        child = self.get_service(child_id)
        urgency = record.get('urgency', self.def_urgency)

        self.logger.info("DO ADD: parent:{}, child:{}, kpi:{} urgency:{}".format(parent_id, child_id, kpi_id, urgency))
        parent_links = self.insert_or_update_links(parent, self.PARENT_LINKS, child_id, kpi_id, urgency)
        child_links = self.insert_or_update_links(child, self.CHILD_LINKS, parent_id, kpi_id)
        self.logger.info("Linking parent {} to child {} with parent-cfg:{} child-cfg:{}".format(parent_id, child_id,
                                json.dumps(parent_links, indent=2), json.dumps(child_links, indent=2)))



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
        kpi_id = record.get('kpiid', "")
        if "" == kpi_id:
            kpi_id = "SHKPI-%s" % child_id
        if None in [parent_id, child_id]:
            raise RuntimeError(
                "Missing required fields parent:{}, child:{}, optional (kpi:{})".format(parent_id, child_id, kpi_id))

        parent = self.get_service(parent_id)
        child = self.get_service(child_id)

        self.logger.info("DO REMOVE: parent:{}, child:{}, kpi:{} ".format(parent_id, child_id, kpi_id))
        self.remove_links(parent[self.PARENT_LINKS], child_id, kpi_id)
        self.remove_links(child[self.CHILD_LINKS], parent_id, kpi_id)


if __name__ == '__main__':
    dispatch(ServiceDependencyCommand, module_name=__name__)
