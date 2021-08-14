#!/usr/bin/env python
# coding=utf-8
#


import unittest
import logging, time
from splunklib import client
from bin.itsi_kvstore import KVStoreHelper

# this has environment specific details like user name and pswd so its not committed in the repo
import test_env as env


class TestCommand(object):
    def __init__(self):
        self.logger = logging.getLogger("TestItsiKvstore")
        try:
            self.service = client.connect(username=env.user, password=env.pswd, host=env.host, port=env.port)
        except:
            raise RuntimeError("can't connect the splunk client")


class TestItsiKvstore(unittest.TestCase):

    def setUp(self):
        self.cmd = TestCommand()
        self.cleanup = []

    def tearDown(self):
        for i in self.cleanup:
            i["kvstore"].delete_object(i["key"])

    def push_cleanup(self, kvstore, key):
        self.cleanup.append({"kvstore":kvstore, "key":key})

    def test_get_uri(self):
        kvstore = KVStoreHelper(self.cmd)
        self.assertEqual(kvstore.get_uri(), "/servicesNS/nobody/SA-ITOA/itoa_interface/service", "path 1 failed")

        kvstore = KVStoreHelper(self.cmd, object_type="typE", api="apI")
        self.assertEqual(kvstore.get_uri(path="pathy"), "/servicesNS/nobody/SA-ITOA/apI/typE/pathy", "path 2 failed")
        self.assertEqual(kvstore.get_uri(), "/servicesNS/nobody/SA-ITOA/apI/typE", "path 3 failed")

    def get_test_entity(self, idx=0):
        """
        These fields are defined in the docs in the create entity example but are not needed
         "_version": "3.0.0",
         "object_type": "entity",
         "_type": "entity"
        """

        ttl = "X_{}".format(time.time())
        return {
            "TEST_NAME": [ttl],
            "TEST_INFO": ["DELETE_ME"],
            "N": [str(idx)],
            "informational": {"fields": ["TEST_INFO", "N"], "values": ["DELETE_ME", str(idx)]},
            "title": ttl,
            "identifier": {"fields": ["TEST_NAME"], "values": [ttl]}
        }

    def xxx_test_create(self):
        kvstore = KVStoreHelper(self.cmd, object_type="entity")
        self.assertEqual(kvstore.get_uri(path="ety"), "/servicesNS/nobody/SA-ITOA/itoa_interface/entity/ety", "get_uri 1 failed")
        cfg = kvstore.create_object(self.get_test_entity())
        self.assertIsNotNone(cfg, "New entity config is None")
        self.assertIsNotNone(cfg['_key'], "New entity config Key is None")
        self.push_cleanup(kvstore,cfg["_key"])
        # if running deletes too soon after the create the kvstore seems to fail to delete it
        # this delays the delete and seems to clean up OK
        """
        for i in range(1, 20):
            self.push_cleanup(kvstore, kvstore.create_object(self.get_test_entity(i))["_key"])
        """
        time.sleep(1)

    def get_test_service(self):
        ttl = "TestSvc_{}".format(int(time.time()))
        return {
            "title": ttl,
            "description": "Service Descirption {} created at ".format(ttl, time.strftime("%F %T"))
        }

    def xxx_test_create_svc(self):
        kvstore = KVStoreHelper(self.cmd)
        svc = kvstore.create_object(self.get_test_service())
        self.assertIsNotNone(svc, "New service config is None")
        self.assertIsNotNone(svc['_key'], "New service config Key is None")
        self.push_cleanup(kvstore, svc["_key"])
        time.sleep(1)

    def test_read_svc(self):
        kvstore = KVStoreHelper(self.cmd)
        cfg = self.get_test_service()
        svc1 = kvstore.create_object(cfg)
        svc2 = kvstore.read_object(svc1["_key"])
        self.push_cleanup(kvstore, svc2["_key"])
        self.assertIsNotNone(svc2, "Service Not Read OK")
        self.assertIn("description", svc2, "Service 2 has no description")
        self.assertEqual(svc2["title"], cfg["title"], "Service title not correct")

    def test_write_svc(self):
        kvstore = KVStoreHelper(self.cmd)
        cfg = self.get_test_service()
        svc_cfg = kvstore.create_object(cfg)
        svc = kvstore.read_object(svc_cfg["_key"])
        # delete it when we are done
        self.push_cleanup(kvstore, svc["_key"])

        self.assertIsNotNone(svc, "Service Not Read OK")
        new_cfg = {
            "title": "New Title",
            "description": "testing a write of a service property"}
        resp = kvstore.write_object(svc["_key"], new_cfg)
        self.assertIsNotNone(resp, "Write 1 failed")
        kvstore.clean_cache()
        svc = kvstore.read_object(svc_cfg["_key"])
        self.assertEqual(svc["title"], new_cfg["title"], "Title not updated")
        self.assertEqual(svc["description"], new_cfg["description"], "Description not updated")


if __name__ == "__main__":
    logging_formats = [
        '%(asctime)s %(levelname)s %(message)s',
        '%(asctime)s %(levelname)s [%(lineno)d:%(module)s:%(funcName)s:%(name)s] >> %(message)s'
    ]
    lvl = "DEBUG"  # "INFO" "WARN"
    logging.basicConfig(level=lvl, format=logging_formats[1])
    logging.warn("Setting log level to %s", lvl)
    unittest.main()
