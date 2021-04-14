#!/usr/bin/env python
# coding=utf-8
#


import unittest
import logging
#from bin.splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import bin.splunklib.client as client
from bin.command_episodeupdate_v2 import UpdateEpisodeCommand


'''
	@classmethod
	def setUpClass(self):
	@classmethod
	def tearDownClass(self):
	def setUp(self):
	def tearDown(self):
'''


class TestEpisodeUpdate(unittest.TestCase):


    @classmethod
    def setUpClass(self):
        '''create a login session'''


    def test_one(self):
        cmd = StubUpdateEpisodeCommand()

        arr = [{'itsi_group_id': '1', 'itsi_policy_id': '1', 'severity': 1, 'status': 1}]
        cmd.stream(arr)
        self.assertEqual(2, 2, "Yes")
        self.assertEqual(1, 1, "No")


    def test_two(self):
        self.assertFalse(False, "test two")


class StubUpdateEpisodeCommand(UpdateEpisodeCommand):
    def __init__(self):
        pswd = "payday$$"  # "testing@splunk"
        user = "admin"
        host = "localhost"
        port = 8089
        service = client.connect(username=user, password=pswd, host=host, port=port)
        self.endpoint = client.Endpoint(service, '/servicesNS/nobody/SA-ITOA/event_management_interface/vLatest')
        self._logger = logging.getLogger("StubUpdateEpisodeCommand")
        self.logger.warn("Overrode Ctor")

    def stream(self, records):
        super(UpdateEpisodeCommand, self).stream(records)


if __name__ == "__main__":
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)

    unittest.main()
