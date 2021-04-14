#!/usr/bin/env python
# coding=utf-8
#
import unittest
import requests, re
from bin.splk import REST_URI, USER, PSWD


class TestMatchTableRex(unittest.TestCase):

    def test_records():
        return [
            {"host": "dcseelm-nt6801234"},
            {"host": "xxxx_seidt-_xxx"},
            {"host": "jhgasdfjhgjhgasd"},
            {"host": "asdmjhasdkjhasd"}
        ]


    class RestStub(object):

        def __init__(self):
            class sinfo:
                def __init__(self, uri, key):
                    self.splunkd_uri = uri
                    self.session_key = key

            class meta:
                def __init__(self, uri, key):
                    self.searchinfo = sinfo(uri, key)

            class Args:
                def __init__(self):
                    self.rest = REST_URI
                    self.user = USER
                    self.pswd = PSWD

            args = Args()
            self._rest = args.rest
            authuri = "{}/services/auth/login".format(args.rest)
            data = {
                "username": args.user,
                "password": args.pswd
            }
            res = requests.post(authuri, data, verify=False)
            res.raise_for_status()
            self._session_key = re.search("<sessionKey>(.*)</sessionKey>", res.text).group(1)

            self._headers = {
                "Authorization": "Splunk %s" % self._session_key,
                "Accept-Encoding": "gzip,deflate",
                "User-Agent": "Python Requests",
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json"
            }

            self.meta = meta(self._rest, self._session_key)


    @classmethod
    def setUpClass(self):
        class sinfo:
            def __init__(self, uri, key):
                self.splunkd_uri = uri
                self.session_key = key

        class meta:
            def __init__(self, uri, key):
                self.searchinfo = sinfo(uri, key)

        class Args:
            def __init__(self):
                self.rest = REST_URI
                self.user = USER
                self.pswd = PSWD
                self.hec = "set_me"
                self.hec_token = "set_me too!@!!"

        args = Args()
        self._rest = args.rest
        authuri = "{}/services/auth/login".format(args.rest)
        data = {
            "username": args.user,
            "password": args.pswd
        }
        res = requests.post(authuri, data, verify=False)
        res.raise_for_status()
        self._session_key = re.search("<sessionKey>(.*)</sessionKey>", res.text).group(1)

        self._headers = {
            "Authorization": "Splunk %s" % self._session_key,
            "Accept-Encoding": "gzip,deflate",
            "User-Agent": "Python Requests",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json"
        }

        self.meta = meta(self._rest, self._session_key)

        self._hec_header = {
            "Authorization": "Splunk {}".format(args.hec_token),
            "Content-Type": "application/json"
        }
        self._hec_url = "{}/services/collector/event".format(args.hec)


    def test_match_row_equals(self):

        #matcher = MatchupCommandRex()
        #matcher.metadata = self.splunkMeta()
        self.assertTrue(True, "test 1")
        self.assertIsNotNone(self._session_key, "Session Key Created")


if __name__ == "__main__":
    '''
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)
    '''

    unittest.main()
