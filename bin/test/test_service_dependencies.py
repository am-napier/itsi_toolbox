#!/usr/bin/env python
# coding=utf-8
#

"""
TODO: implement kvstore clean up
Running this test creates objects in the server associated through the env settings
Currently there is no auto clean up like delete all services and entities etc based on naming convention
"""


import unittest, json
import logging
from splunklib import client
from bin.command_service_dependency import ServiceDependencyHelper
from bin.itsi_kvstore import KVStoreHelper
from test_objects import TestObjects

# this has environment specific details like user name and pswd so its not committed in the repo
import test_env as env


class TestCommand(object):
    def __init__(self, mode="add", default_urgency=4):
        self.opt_mode = mode
        self.def_urgency = default_urgency
        self.logger = logging.getLogger("TestServiceDependencies")
        try:
            self.service = client.connect(username=env.user, password=env.pswd, host=env.host, port=env.port)
        except Exception as e:
            self.logger.error("can't connect the splunk client {}".format(e))

    def default_urgency(self, v=None):
        if v is not None:
            self.def_urgency = v
        return self.def_urgency


class TestServiceDependencies(unittest.TestCase):

    def setUp(self):
        self.cmd = TestCommand()
        self.kvstore = KVStoreHelper(self.cmd)
        self.to = TestObjects(self.cmd)
        self.test_svcs = {
            "a1": self.to.get_test_svc("test_a", "A One")
            ,"a2": self.to.get_test_svc("test_a", "A Two")
            ,"a3": self.to.get_test_svc("test_a", "A Three")
            ,"a4": self.to.get_test_svc("test_a", "A Four")
        }

    def tearDown(self):
        pass

    """
    get_links
    do_add
    do_remove
    """
    def test_urgency(self):
        self.cmd.default_urgency(3)
        command = ServiceDependencyHelper(self.cmd)
        self.assertEqual(command.def_urgency, 3, "default_urgency is wrong")


    def test_insert_or_update_links(self):
        a1 = self.test_svcs["a1"]
        a2 = self.test_svcs["a2"]
        self.assertIsNotNone(a1, "A1 is null")
        self.assertIsNotNone(a2, "A2 is null")
        command = ServiceDependencyHelper(self.cmd)
        kpi = next((item for item in a2["kpis"] if item['title'] == "custom_1"), None)
        self.assertIsNotNone(kpi, "Test KPI is None")
        parent_link = command.insert_or_update_links(a1, command.PARENT_LINKS, a2["_key"], kpi["_key"], urgency=6)
        self.assertIsNotNone(parent_link, "Parent link is None")
        self.assertIn("serviceid", parent_link, "Parent link doesn't contain serviceid")
        self.assertIn("kpis_depending_on", parent_link, "Parent link doesn't contain kpis_depending_on")
        self.assertIn("overloaded_urgencies", parent_link, "Parent link doesn't contain overloaded_urgencies")
        self.assertEqual(parent_link["serviceid"], a2["_key"], "Parent link service id is wrong")
        self.assertIn(kpi["_key"], parent_link["kpis_depending_on"], "Parent link doesn't contain KPI key")

        child_link = command.insert_or_update_links(a2, command.CHILD_LINKS, a1["_key"], kpi["_key"])
        self.assertIsNotNone(child_link, "Child link is None")
        self.assertIn("serviceid", child_link, "Child link doesn't contain serviceid")
        self.assertIn("kpis_depending_on", child_link, "Child link doesn't contain kpis_depending_on")
        self.assertNotIn ("overloaded_urgencies", child_link, "Child link contains overloaded_urgencies")

    def test_do_add(self):
        '''
        setup this structure
        a1 -> a2.SHS, a2.custom_1(1)
        '''
        a1 = self.test_svcs["a1"]
        a2 = self.test_svcs["a2"]
        a3 = self.test_svcs["a3"]
        a4 = self.test_svcs["a4"]
        self.assertIsNotNone(a1, "A1 is null")
        self.assertIsNotNone(a2, "A2 is null")
        self.assertIsNotNone(a3, "A3 is null")
        self.assertIsNotNone(a4, "A4 is null")
        command = ServiceDependencyHelper(self.cmd)
        a2_shs = next((item for item in a2["kpis"] if item['title'] == "ServiceHealthScore"), None)
        a2_c1 = next((item for item in a2["kpis"] if item['title'] == "custom_1"), None)

        a3_shs = next((item for item in a3["kpis"] if item['title'] == "ServiceHealthScore"), None)
        a3_c1 = next((item for item in a3["kpis"] if item['title'] == "custom_1"), None)
        a3_c2 = next((item for item in a3["kpis"] if item['title'] == "custom_2"), None)

        self.assertIsNotNone(a2_shs, "Test KPI a2_shs is None")
        p1 = command.do_add({"parent":a1["_key"], "child": a2["_key"], "kpiid":a2_shs["_key"]})
        p2 = command.do_add({"parent":a1["_key"], "child": a2["_key"], "kpiid":a2_c1["_key"], "urgency":1})
        p1 = command.do_add({"parent": a1["_key"], "child": a3["_key"], "kpiid": a3_shs["_key"]})
        p1 = command.do_add({"parent": a1["_key"], "child": a3["_key"], "kpiid": a3_c1["_key"]})
        p1 = command.do_add({"parent": a1["_key"], "child": a3["_key"], "kpiid": a3_c2["_key"]})

        """
        command.do_remove({"parent":a1["_key"], "child": a2["_key"], "kpiid":a2_shs["_key"]})
        command.do_remove({"parent":a1["_key"], "child": a2["_key"], "kpiid":a2_c1["_key"], "urgency":1})
        command.do_remove({"parent": a1["_key"], "child": a3["_key"], "kpiid": a3_shs["_key"]})
        command.do_remove({"parent": a1["_key"], "child": a3["_key"], "kpiid": a3_c1["_key"]})
        command.do_remove({"parent": a1["_key"], "child": a3["_key"], "kpiid": a3_c2["_key"]})
        """

    def xxtest_do_remove(self):
        a1 = self.test_svcs["a1"]
        a2 = self.test_svcs["a2"]
        payload = [
            {"_key" : a1["_key"], "description" : "thisisa1", "title":a1["title"], "object_type":"service"},
            {"_key" : a2["_key"], "description" : "thisisa2", "title":a2["title"], "object_type":"service"}
        ]
        resp = self.kvstore.write_bulk(json.dumps(payload))



    def xtest_do_update(self):
        self.assertFalse(True, "update not implemented")

if __name__ == "__main__":
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)

    unittest.main()
