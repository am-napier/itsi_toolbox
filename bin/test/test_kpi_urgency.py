#!/usr/bin/env python
# coding=utf-8
#

"""
Used this just to test the helper object does what I think it should
"""


import unittest, json
import logging
from splunklib import client
from bin.command_kpi_urgency import KpiUrgencyHelper
from bin.itsi_kvstore import KVStoreHelper
from make_test_objects import MakeTestObjects

# this has environment specific details like user name and pswd so its not committed in the repo
import test_env as env


class TestCommand(object):
    def __init__(self, default_urgency=4):
        self.def_urgency = default_urgency
        self.logger = logging.getLogger("TestKpiUrgency")
        try:
            self.service = client.connect(username=env.user, password=env.pswd, host=env.host, port=env.port)
        except Exception as e:
            self.logger.error("can't connect the splunk client {}".format(e))

    def default_urgency(self, v=None):
        if v is not None:
            self.def_urgency = v
        return self.def_urgency


class TestKpiUrgency(unittest.TestCase):

    def setUp(self):
        self.cmd = TestCommand()
        self.kvstore = KVStoreHelper(self.cmd)
        self.to = MakeTestObjects(self.cmd)
        try:
            self.test_svcs = {
                "a1": self.to.get_test_svc("test_a", "A_Test_One")
            }
        except Exception as e:
            logging.getLogger("TestKpiUrgency-setup").error("Setup failed: ", e)
            print "Error is setup is : {}".format(e)

    def tearDown(self):
        pass

    """
    
    """
    def test_urgency(self):
        self.cmd.default_urgency(3)
        command = KpiUrgencyHelper(self.cmd)
        self.assertEqual(command.def_urgency, 3, "default_urgency is wrong")


    def test_update(self):
        a1 = self.test_svcs["a1"]
        self.assertIsNotNone(a1, "A1 is null")
        command = KpiUrgencyHelper(self.cmd)
        kpi_1 = next((item for item in a1["kpis"] if item['title'] == "custom_1"), None)
        kpi_2 = next((item for item in a1["kpis"] if item['title'] == "custom_2"), None)
        self.assertIsNotNone(kpi_1, "Test KPI-1 is None")
        self.assertIsNotNone(kpi_2, "Test KPI-2 is None")

        kpi = command.update(dict(service=a1["_key"], kpiid=kpi_1["_key"], urgency=6))
        self.assertIsNotNone(kpi, "payload returned is None")
        self.assertEqual(kpi["urgency"], 6, "Urgency was not updated")


if __name__ == "__main__":
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)

    unittest.main()
