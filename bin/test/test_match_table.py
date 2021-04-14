#!/usr/bin/env python
# coding=utf-8
#


import unittest
import logging
from collections import OrderedDict
from bin.match_table import MatchValue, MatchRow, MatchTable

'''
	@classmethod
	def setUpClass(self):
	@classmethod
	def tearDownClass(self):
	def setUp(self):
	def tearDown(self):
'''
def test_row(a, b, c, d, desc):
    return {"a": a, "b": b, "c": c, "d": d, "desc": desc}

class TestMatchTable(unittest.TestCase):


    @classmethod
    def setUpClass(self):
        self.table = MatchTable("a,b,c,d".split(","))
        self.table.add_row(test_row("a*",     "b1*",    "c*",   "d1", "row 1"))
        self.table.add_row(test_row("a1*",    "b11*",   "c1",   "d2", "row 2"))
        self.table.add_row(test_row("a11*",   "b111*",  "c1",   "d3", "row 3"))
        self.table.add_row(test_row("a111*",  "b1111*", "c1",   "d4", "row 4"))
        self.table.add_row(test_row("*a2",    "*1*",    "c1",   "d5", "row 5"))
        self.table.add_row(test_row("apples", "b*",     "c1",   "d6", "row 6"))
        self.table.add_row(test_row("*aa2",   "b*",     "c1",   "d7", "row 7"))
        self.table.add_row(test_row("aaaa2",  "b*",     "c1",   "d8", "row 8"))
        self.table.add_row(test_row("*a*",    "*",      "*",    "d9", "row 9"))

        self.table.add_row(test_row("*aa*",     "b", "c", "d", "row 20"))
        self.table.add_row(test_row("*aaa*",    "b", "c", "d", "row 21"))
        self.table.add_row(test_row("*aaa*",    "b", "c", "d", "row 22"))
        self.table.add_row(test_row("*aaaa*",   "b", "c", "d", "row 23"))
        self.table.add_row(test_row("*aaaa",    "b", "c", "d", "row 24"))
        self.table.add_row(test_row("aaaa*",    "b", "c", "d", "row 25"))

        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "d",      "row 26"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "dd",     "row 27"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "ddd",    "row 28"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "*dddd",  "row 29"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "dddd*",  "row 30"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "*d*",    "row 31"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "*dd*",   "row 32"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "*ddd*",  "row 33"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "*dddd*", "row 34"))
        self.table.add_row(test_row("aaaaaa", "bxbxbx", "cxcxcx", "*",      "row 35"))


    def test_match_table(self):
        tbl = self.table._match("a", "a")
        self.assertEqual(tbl.len(), 2, "Table has two matches for a")

        d = test_row("a11", "b111", "c1", "d1", "test event 1")
        row = self.table.match_table(d)
        self.assertIsNotNone(row, "Tested cols a,b,c not None")
        self.assertEqual("a*", row["a"], "Tested cols a,b,c a is a*")
        self.assertEqual("row 1", row["desc"], "Tested cols a,b,c desc is row 1")

        row = self.table.match_table(d)
        self.assertIsNotNone(row, "Tested cols a,b,c,d not None")

        row = self.table.match_table({"a":"aaaaaa", "b":"bxbxbx", "d": "dddddddddd 10 d's", "c": "cxcxcx", "desc": "dddddddddd 10 d's, should match row 30"})
        self.assertEqual("row 30", row["desc"], "a,b and d - match row 30")
        #self.assertEqual(
        #    self.table.match_table({"a":"aaaaaa", "d": "xx dddd xx"}, "a,d".split(","))["desc"],
        #    "row 34", "a,b and d - match row 34")
        #self.assertEqual(
        #    self.table.match_table({"d": "ddd"}, "d".split(","))["desc"],
        #    "row 28", "d - match row 28")

        #self.assertIsNone(
        #    self.table.match_table({"d": "ddd"}, "xxx".split(",")),
        #    "xxx - None objec for missing key")


    def test_no_matches(self):
        d = test_row("a11", "b11", "c1", "xxx", "test event 1")
        res = self.table.match_table(d)
        self.assertIsNone(res, "Empty Match returned")

        # note this will fail to match if the property isn't passed, ie * != NULL
        self.assertIsNone(
            self.table.match_table({"foo" : "bah"}),
            "cols not present imn passed event doesn't barf")

    def test_prune_rows(self):
        '''
        need to test that prune_rows is getting the right matched values back
        '''
        self.assertFalse(False, "unimplemented test case prune_rows")

class TestMatchRow(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.raw_row = {"a": "App*", "b": "*Bananas", "c": "*Cherry*", "d": "Duran"}
        self.row = MatchRow(self.raw_row, "a,b,c,d".split(","))

    def test_match_row_equals(self):
        d = {"a" : "Apples", "b" : "Bananas", "c":"Cherry", "d" : "Duran"}
        row = MatchRow(d, "a,b,c,d".split(","))
        matched = row.match_row("a", "Apples")
        self.assertTrue(matched[0], "Matched Apples to ^Apples$ boolean")
        # test Priority 0=any, 1=contains, 2=start/ends with (default) , 3=equals
        self.assertEqual(matched[1], 3, "Matched Apples exactly prio=3")
        # test length of match string
        self.assertEqual(matched[2], 6, "Matched Apples to ^Apples$ match string length")

        self.assertFalse(row.match_row("a", "Apple")[0], "Not Matched apple")
        self.assertFalse(row.match_row("a", "apples")[0], "Not Matched apples")

    def test_match_row_startswith(self):
        # note this uses the class property so these apples is different to them apples in the method above
        matched = self.row.match_row("a", "Apples")
        self.assertTrue(matched[0], "Matched Apples boolean to App*")
        # test Priority 0=any, 1=contains, 2=start/ends with (default) , 3=equals
        self.assertEqual(matched[1], 2, "Matched Apples to App* starts-with prio=2")
        # test length of match string
        self.assertEqual(matched[2], 4, "Matched Apples match string length App*")

        self.assertTrue(self.row.match_row("a", "Apples")[0], "Apples starts with App*")
        self.assertFalse(self.row.match_row("a", "apples")[0], "apples starts with App* but case is wrong")
        self.assertFalse(self.row.match_row("a", "CrabApple")[0], "Doesn't start with Apple")


    def test_match_row_endswith(self):
        # *Bananas
        self.assertTrue(self.row.match_row("b", "My Bananas")[0], "*Bananas with My Bananas")
        self.assertFalse(self.row.match_row("b", "My BanaNAS")[0], "*Bananas My Bananas is False")
        self.assertTrue(self.row.match_row("b", "Bananas")[0], "Bananas extact should match")

    def test_match_row_contains(self):
        # *Cherry*
        self.assertTrue(self.row.match_row("c", "Cherry Pie")[0], "Cherry Pie")
        self.assertTrue(self.row.match_row("c", "My Cherry Pie")[0], "Cherry Pie")
        self.assertTrue(self.row.match_row("c", "Sour Cherry")[0], "Sour Cherry")

        self.assertFalse(self.row.match_row("c", "herr")[0], "Cherry Pie - herr")


class TestMatchValue(unittest.TestCase):

    def DEPRICATED_test_patterns_for_rex(self):
        self.assertEqual(MatchValue("x", "abc")._pattern, "^abc$", "equals matches")
        self.assertEqual(MatchValue("x", "abc*")._pattern, "^abc", "startswith matches")
        self.assertEqual(MatchValue("x", "*abc")._pattern, "abc$", "endswith matches")
        self.assertEqual(MatchValue("x", "*abc*")._pattern, "abc", "contains matches")
        self.assertEqual(MatchValue("x", "a*bc")._pattern, "^a*bc$", "2 equals matches")
        self.assertEqual(MatchValue("x", "a*bc*")._pattern, "^a*bc", "2 startswith matches")
        self.assertEqual(MatchValue("x", "*a*bc")._pattern, "a*bc$", "2 endswith matches")
        self.assertEqual(MatchValue("x", "*a*bc*")._pattern, "a*bc", "2 contains matches")

    def test_patterns(self):
        self.assertEqual(MatchValue("x", "abc")._pattern, "abc", "equals matches")
        self.assertEqual(MatchValue("x", "abc*")._pattern, "abc", "startswith matches")
        self.assertEqual(MatchValue("x", "*abc")._pattern, "abc", "endswith matches")
        self.assertEqual(MatchValue("x", "*abc*")._pattern, "abc", "contains matches")
        self.assertEqual(MatchValue("x", "a*bc")._pattern, "a*bc", "2 equals matches")
        self.assertEqual(MatchValue("x", "a*bc*")._pattern, "a*bc", "2 startswith matches")
        self.assertEqual(MatchValue("x", "*a*bc")._pattern, "a*bc", "2 endswith matches")
        self.assertEqual(MatchValue("x", "*a*bc*")._pattern, "a*bc", "2 contains matches")


    def test_match_value_equals(self):
        v = MatchValue("col-a", "abc")
        self.assertEqual(v._key, "col-a", "Key is set correctly")
        test_str = "abc"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "abc--"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--abc"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--abc--"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)

    def test_match_value_startswith(self):
        v = MatchValue("col-a", "abc*")
        test_str = "abc"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "abc--"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--abc"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--abc--"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)

    def test_match_value_endswith(self):
        v = MatchValue("col-a", "*abc")
        test_str = "abc"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--=--=--.*abc"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "----abc-----"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--[abc]+"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)

    def test_match_value_any(self):
        v = MatchValue("col-a", "*")
        test_str = "abc"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--=--=--.*abc"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "----abc-----"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--[abc]+"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)

    def test_match_value_contains(self):
        v = MatchValue("col-a", "*abc*")
        test_str = "abc"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--=--=--.*abc=--=----"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "----abc-----"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "--[abc]+"
        self.assertTrue(v.match_value(test_str)[0], "test string match for " + test_str)

        test_str = "bc"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = ".bc"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)
        test_str = "..c"
        self.assertFalse(v.match_value(test_str)[0], "test string match for " + test_str)

if __name__ == "__main__":
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)

    unittest.main()
