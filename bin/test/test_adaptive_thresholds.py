#!/usr/bin/env python
# coding=utf-8
#


import unittest
import logging
from splunklib import client
from bin.command_adaptive_thresholds import AdaptiveThresholdHelper, DEF_FIELDS

# this has environment specific details like user name and pswd so its not committed in the repo
import test_env as env


'''
	@classmethod
	def setUpClass(self):
	@classmethod
	def tearDownClass(self):
	def setUp(self):
	def tearDown(self):
'''

class TestCommand(object):
    def __init__(self, mode="read", format="flat", fields=DEF_FIELDS):
        self.service = client.connect(username=env.user, password=env.pswd, host=env.host, port=env.port)
        self.opt_mode = mode
        self.opt_format = format
        self.opt_fields = fields
        self.logger = logging.getLogger("TestAdaptiveThresholdsHelper")
        #cx = splunklib.binding.connect(username=user, password=pswd, host=host, port=port)


class TestAdaptiveThresholdsHelper(unittest.TestCase):

    def setUp(self):
        '''
        look away now or get with the growth mindset
        how can we test these methods that need live ids for real config?
        we could build stuff to discover a service and a kpi or fake the unit testing.

        Option 1 for now ... I just want to debug this in my IDE :-O Sorry test police #epicfail

        Fix this oversight if you have time
        '''
        #self.svc_id = "01445a82-2d99-4587-91e7-e9f9e283fa63"
        #self.kpi_id = "95e3ffec3ddc4d17525f717d"


    def test_flat_read(self):
        self.cmd = AdaptiveThresholdHelper(TestCommand(fields="adaptive_thresholds_is_enabled,tz_offset"))
        self.assertIsNotNone(self.cmd, "Helper exists")
        svc = self.cmd.read_service(self.svc_id)
        self.assertIsNotNone(svc, "read service object from kvstore")
        self.assertEqual(svc['_key'], self.svc_id, "we didn't get a valid _key back from the kvstore")
        rec = {"blah": "de blah"}
        self.cmd.do_read(self.svc_id, self.kpi_id, rec)
        self.assertEqual(rec['blah'], "de blah", "record was trashed during update")
        self.assertEqual(len(rec.keys()), 3, "Not enough keys returned from do_read:text")


    def test_json_read(self):
        self.cmd = AdaptiveThresholdHelper(TestCommand(format="json"))
        self.assertIsNotNone(self.cmd, "Helper exists")
        svc = self.cmd.read_service(self.svc_id)
        self.assertIsNotNone(svc, "read service object from kvstore")
        self.assertEqual(svc['_key'], self.svc_id, "we didn't get a valid _key back from the kvstore")
        rec = {"blah": "de blah"}
        self.cmd.do_read(self.svc_id, self.kpi_id, rec)
        self.assertEqual(rec['blah'], "de blah", "record was trashed during update")
        self.assertEqual(len(rec.keys()), 2, "Not enough keys returned from do_read:json")

    def test_update(self):
        cmd = AdaptiveThresholdHelper(TestCommand(mode="write"))
        cmd_read = AdaptiveThresholdHelper(TestCommand(mode="read", fields="adaptive_thresholds_is_enabled"))
        self.assertIsNotNone(cmd, "Helper exists")
        rec = {"enabled": "false"}
        cmd.do_update(self.svc_id, self.kpi_id, rec)
        cmd.write_cache()
        rec_read = {}
        cmd_read.do_read(self.svc_id, self.kpi_id, rec_read)



if __name__ == "__main__":
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)

    unittest.main()
