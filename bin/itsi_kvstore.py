#!/usr/bin/env python
# coding=utf-8
#
import json

class KVStoreHelper(object):

    def __init__(self, command, object_type="service", api="itoa_interface"):
        self._cache = {}
        self.service = command.service
        self.logger = command.logger
        self._api = api
        self._type = object_type

    def get_uri(self, path=None):
        return '/servicesNS/nobody/SA-ITOA/{}/{}{}'.format(self._api, self._type, "" if path is None else "/"+path)

    def write_bulk(self, data):
        """
        Write the data as partial objects to the relevant kvstore type and api
        params:
          data - string payload to write, we don't call the json.dump here please do that first
        """
        params = {
            "is_partial_data": 1,
            "body": data
        }
        return self.handle_response(self.service.post(self.get_uri("bulk_update"), **params), "write_bulk")

    def handle_response(self, response, context):
        status = int(response['status'])
        self.logger.info('handle_response status={} context={}'.format(status, context))
        if status > 299:
            raise RuntimeError("POST failed in {}, response was {}".format(context, response))
        elif status == 204:
            return True #no content to return
        else:
            return json.loads(response['body'].read())


    def write_cache(self):
        '''
        todo - implement this as write bulk
        '''
        raise RuntimeError("this is a garbage design idea, don't do it, we don't have to be efficient here, JDI!!")
        if len(self._cache) == 0:
            self.logger.info("Cache is empty, no writes to do.")
            return
        data = []
        for id in self._cache:
            cfg = self._cache[id]
            query = {"body": json.dumps(cfg)}
            resp = self.service.post(self.get_uri(path=id), **query)
            if resp and resp['status'] > 299:
                self.logger.error("Failed writing service with id {} returned status {}".format(id))
                self.logger.error("Status {}".format(resp['status']))
                self.logger.error("Body {}".format(resp['body'].read()))
                raise Exception("write service failed, check logs")
            self.logger.info("update completed for svc:{} id:{}".format(cfg['title'], id))

    def read_object(self, key):
        """
        """
        if key is None:
            return None
        if key in self._cache:
            self.logger.debug("read_service cache hit")
            return self._cache[key]
        else:
            self.logger.debug("read_service cache miss")
            resp = self.service.get(self.get_uri(key))
            self._cache[key] = self.handle_response(resp, "read_object")
            return self._cache[key]

        # should be dead code but this could help in debugging
        self.logger.error("Reading service with id:{} returned status:{}, body:{}".format(
            key, resp['status'], resp['body'].read()))
        raise RuntimeError("read service id={} failed, status={} check logs for body details".format(key, resp['status']))


    def create_object(self, body=None):
        params = {"body": json.dumps(body)}
        try:
            resp = self.service.post(self.get_uri(), **params)
            cfg = self.handle_response(resp, "create_object")
        except Exception as e:
            # failures to do this might mean the payload needs encoding
            self.logger.error("Failed to create object, possible encoding ie % in the search? : {}".format(e))
        return cfg

    def delete_object(self, key):
        uri = self.get_uri(key)
        self.logger.info("deleting at URI {}".format(uri))
        return self.handle_response(self.service.delete(uri), "delete_object")

    def write_object(self, key, cfg, is_partial=True):
        uri = self.get_uri(key)

        self.logger.info("writing object {}".format(uri))
        payload = {
            "is_partial": is_partial,
            "body": json.dumps(cfg)
        }
        return self.handle_response(self.service.post(uri, **payload), "write_object")

    def clean_cache(self):
        self._cache.clear()
