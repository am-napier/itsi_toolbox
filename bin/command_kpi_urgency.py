#!/usr/bin/env python
# coding=utf-8
#
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
#from splunklib.client import Endpoint

import time
from itsi_kvstore import KVStoreHelper


#from perf import Perf

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


@Configuration()
class KpiUrgencyCommand(StreamingCommand):
    """
    eval serviceid=yyy kpiid=zzz urgency=7 | kpiurgency
    """

    def_urgency = Option(
        doc='''
        **Syntax:** **default_urgency=***int*
        **Description:** value between 0 and 11
        **Default:** 5''',
        name='default',
        require=False,
        default=5,
        validate=validators.Integer())

    debug = Option(
        doc='''
        **Syntax:** **debug=***boolean*
        **Description:** toggles extra debug in the output
        **Default:** false''',
        name='debug',
        require=False,
        default=False,
        validate=validators.Boolean())

    # region Command implementation
    def __init__(self):
        super(KpiUrgencyCommand, self).__init__()


    def prepare(self):
        pass

    def stream(self, records):
        """
        Process all events.
        :param records: An iterable stream of events from the command pipeline.
        :return: `None`.
        """
        self.logger.info('KPI Urgency Command entering stream.')
        t1 = time.time()

        # Put your event transformation code here
        helper = KpiUrgencyHelper(self)
        for record in records:
            # delete this before production
            self.logger.info('Stream Record {0}'.format(record))
            t2 = time.time()

            try:
                record['new_kpi'] = helper.update(record)
            except Exception as e:
                record["ErrorMessage"] = "Error, check Service and KPI ids, message was: %s " % str(e)

            self.logger.info("complete in {} secs".format(time.time() - t2))
            yield record

        self.logger.info("Full update time is:{}".format(time.time() - t1))

    # endregion


class KpiUrgencyHelper(object):
    """
    This class is here to help with unit testing
    """
    def __init__(self, command):
        self.logger = command.logger
        self.def_urgency = command.def_urgency
        self.kvstore = KVStoreHelper(command)
        self.KPIS = "kpis"

    def update(self, record):

        service_id = record.get("service_id", None)
        kpi_id = record.get('kpi_id', "")
        if "" == kpi_id:
            kpi_id = "SHKPI-%s" % service_id
        if None in [service_id, kpi_id]:
            raise RuntimeError(f"Missing required fields service:{service_id}, optional (kpi:{kpi_id})")
        service = self.kvstore.read_object(service_id)["body"]
        urgency = record.get('urgency', self.def_urgency)

        self.logger.info("DO UPDATE: service:{}, kpi:{} urgency:{}".format(service_id, kpi_id, urgency))
        kpi = next((item for item in service["kpis"] if item['_key'] == kpi_id), None)
        if kpi:
            kpi["urgency"] = urgency
            return kpi #dict(_key=service_id,object_type="service", title=service["title"], kpis=service[self.KPIS])
        return None


if __name__ == '__main__':
    dispatch(KpiUrgencyCommand, module_name=__name__)
