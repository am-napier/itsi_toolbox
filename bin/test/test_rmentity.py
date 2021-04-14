#!/usr/bin/env python
# coding=utf-8
#


import unittest
import logging
#from bin.splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import bin.splunklib.client



'''
	@classmethod
	def setUpClass(self):
	@classmethod
	def tearDownClass(self):
	def setUp(self):
	def tearDown(self):
'''


class TestRMEntity(unittest.TestCase):


    @classmethod
    def setUpClass(self):
        pass


    def test_one(self):
        self.assertEqual(2, 2, "Yes")
        self.assertEqual(1, 1, "No")


    def test_two(self):
        self.assertFalse(False, "test two")



if __name__ == "__main__":
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)

    unittest.main()
