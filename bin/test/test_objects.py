import os, sys, json, uuid, time
from bin.itsi_kvstore import KVStoreHelper



class TestObjects(KVStoreHelper):
    """Create config objects in the kvstore to help with testing"""
    def __init__(self, command, object_type="service", api="itoa_interface"):
        """command has both a service and logger object"""
        self._cache = {}
        self.service = command.service
        self.logger = command.logger
        self._api = api
        self._type = object_type

    def get_uuid(self, *args):
        """
        Create a test UUID prefixed with UNIT_TEST for make things that go into the kvstore
        returns: string
        """
        str = "UNIT_TEST"
        for i in args:
            str = "{}--{}".format(str, i)
        keep = ('-', '_')
        return "".join(c for c in str if c.isalnum() or c in keep).rstrip()

    def get_test_svc(self, file_name, svc_name):
        """Create testing services only if they don't exist in the kvstore"""
        svc_id = self.get_uuid("svc", svc_name)
        try:
            return self.read_object(svc_id)
        except:
            with( open("./test_data/{}.json".format(file_name) ) ) as fp:
                svc = json.loads(fp.read())
                svc["_key"] = svc_id
                svc["title"] = svc_name
                self.create_object(self.fix_kpis(svc))
            return self.read_object(svc_id)

    def get_kpi_called(self, svc, kpi_name):
        return next((item for item in svc["kpis"] if item['title'] == kpi_name), None)

    # this is a destructive method and WILL change the contents of svc in two ways
    # 1. the service_health KPI will be removed because if it exists in the template when its created
    #    then it gets added twice
    # 2. there are no UUIDs assigned for the KPIs so add them
    def fix_kpis(self, svc):
        # fix the UUIDs cause there aren't any set
        # remove the service health KPI or it gets created twice
        """        for k in svc['kpis']:
                    k['_key'] = self.get_uuid("kpi", k["title"], time.time())
        """
        kpis = []
        svc_id = svc["_key"]
        for kpi in svc['kpis']:
            if kpi['type'] != "service_health":
                kpi['_key'] = self.get_uuid("kpi", svc_id, kpi["title"])
                kpi["serviceid"] = svc_id
                kpis.append(kpi)
        svc['kpis'] = kpis
        return svc