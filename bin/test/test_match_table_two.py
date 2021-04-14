#!/usr/bin/env python
# coding=utf-8
#


import unittest
import logging
from collections import OrderedDict
from bin.match_table import MatchValue, MatchRow, MatchTable
import csv, bin.perf

'''
	@classmethod
	def setUpClass(self):
	@classmethod
	def tearDownClass(self):
	def setUp(self):
	def tearDown(self):
'''


class TestMatchTableBulk(unittest.TestCase):


    @classmethod
    def setUpClass(self):
        logging_formats = [
            '%(asctime)s %(levelname)s %(message)s',
            '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
        ]
        lvl = "INFO"  # "INFO" "WARN"
        logging.basicConfig(level=lvl, format=logging_formats[1])
        logging.warn("Setting log level to %s", lvl)
        self.logger = logging.Logger.manager.getLogger(self.__class__.__name__)

        #read the file test_match_table_bulk.csv and load that
        self.table = MatchTable("A,B,C,D,E,F".split(","))
        with open("./data/test_match_table_bulk.csv", "r") as fp:
            tbl = csv.DictReader(fp)
            for r in tbl:
                self.table.add_row(r)

        self.perf = bin.perf.Perf(self.logger)

    def make_test_row(self, str):
        ll = str.split(",")
        return {
            "A":ll[0], "B":ll[1],"C":ll[2], "D":ll[3],"E":ll[4], "F":ll[5]
        }

    def test_match_table_small(self):
        events = []
        with open("./data/test_match_table_foo.csv", "r") as fp:
            tbl = csv.DictReader(fp)
            for r in tbl:
                events.append(r)

        self.perf.start("Test 1 - A")
        failed = 0
        for e in events:
            row = self.table.match_table(e)
            failed = 1 if row is None else 0
        t1 = self.perf.end("Test 1 - A")
        self.assertEqual(0, failed, "Failed Matches - non optimised")

        self.perf.start("Test 1 - B")
        failed = 0
        for e in events:
            row = self.table.match_table_optimised(e)
            failed = 1 if row is None else 0
        self.assertEqual(0, failed, "Failed Matches - optimised")

        t2 = self.perf.end("Test 1 - B")

        self.assertLess(t2, t1, "optimisation test is slower")


if __name__ == "__main__":
    unittest.main()
