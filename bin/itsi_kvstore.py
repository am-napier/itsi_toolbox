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
        '''create the REST call for the expected object type, no filters are added here'''
        _path = "" if path is None else "/"+path
        return f'/servicesNS/nobody/SA-ITOA/{self._api}/{self._type}{_path}'

    def write_bulk(self, data):
        """
        Write the data as partial objects to the relevant kvstore type and api
        params:
          data - string payload to write, we don't call the json.dump here please do that first
        """
        params = {
            "is_partial_data": 1,
            "body": json.dumps(data)
        }
        return self.handle_response(self.service.post(self.get_uri("bulk_update"), **params), "write_bulk")

    def handle_response(self, response, context):
        status = int(response['status'])
        if status > 299:
            raise RuntimeError("Request failed in {}, response was {}".format(context, response))

        try:
            body=json.loads(response['body'].read())
            self.logger.debug('handle_response response {} body{} status={} context={}'.format(response, body, status, context))
        except:
            body=""

        self.logger.debug(f'BODDDY :{body}')
        return {
            "status":response['status'],
            "body": body,
            "reason":response['reason']
        }


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
        read the object from the cache if its there or get from the cache and return it
        Not thread safe as there is no lock on the kvstore object.
        Add switch to force read from kvstore under all conditions except where explicitly directed.
        """
        if key is None:
            return None
        if key in self._cache:
            self.logger.debug("read_service cache hit")
            return self._cache[key]
        else:
            self.logger.info("read_service cache miss")
            resp = self.service.get(self.get_uri(key))
            self._cache[key] = self.handle_response(resp, "read_object")
            return self._cache[key]

        # should be dead code but this could help in debugging
        self.logger.error("Reading service with id:{} returned status:{}, body:{}".format(
            key, resp['status'], resp['body'].read()))
        raise RuntimeError("read service id={} failed, status={} check logs for body details".format(key, resp['status']))

    def read_list(self, filter, fields=[]):
        '''
        reads a set of objects using a filter and for a given set of fields
        could be a huge data set if abused so caller needs to be careful what they ask for
        No caching will be done here
        @param: filter (string) is a mongo filter for records, ie {"title":{"$regex":"^ACME"}} all objects starting with ACME
        @param: fields (list) list of fields to return
        @returns: list of objects read from kvstore
        '''
        fields = self.get_fields(fields)
        params = {
            "filter": filter,
            "fields": ",".join(fields)
        }
        uri = self.get_uri()
        self.logger.info(f'[kvstore] [read_list] uri_is={uri}, params={params}')
        resp = self.service.get(uri, **params) 
        # only because I don't know better
        res = self.handle_response(resp, "read_list")
        if len(fields)==0:
            # if all fields are requested return the whole array
            return res
        else:
            # explict fields were request so drop the extraneous fields
            new_res=[]    
            for r in res:
                tmp = {}
                new_res.append(tmp)
                for k in r:
                    if k in fields:
                        tmp[k] = r[k]
            return new_res


    def create_object(self, body=None):
        '''Create an object in the kvstore using the body param as an optional template'''
        params = {"body": json.dumps(body)}
        try:
            resp = self.service.post(self.get_uri(), **params)
            cfg = self.handle_response(resp, "create_object")
        except Exception as e:
            # failures to do this might mean the payload needs encoding
            self.logger.error("Failed to create object, possible encoding ie % in the search? : {}".format(e))
        return cfg


    def delete_object(self, key):
        '''
        delete the given object from the kvstore
        '''
        uri = self.get_uri(key)
        self.logger.info("deleting at URI {}".format(uri))
        return self.handle_response(self.service.delete(uri), "delete_object")


    def write_object(self, key, cfg, is_partial=True):
        '''
        write/update the specified object in the kvstore
        '''
        uri = self.get_uri(key)

        self.logger.info("writing object {}".format(uri))
        payload = {
            "is_partial": 1 if is_partial else 0,
            "body": json.dumps(cfg)
        }
        self.logger.info(f'URI:{uri}, params: {json.dumps(payload)}')
        return self.handle_response(self.service.post(uri, **payload), "write_object")


    def clean_cache(self):
        '''
        clear the cache from local memory
        '''
        self._cache.clear()


    def get_filter(self, field, value=None, regex=None, quote=True):
        '''
        Creates a filter string to query the kvstore.  If you need it more complex then DIY it.
        '''
        qt = '"' if quote else ""
        if value is not None:
            return '{"%s" : %s%s%s}' % (field, qt, value, qt)
        elif regex is not None:
            return '{"%s" : {"$regex" : "%s"}}' % (field, regex)
        else:
            raise ValueError("get_filter must be passed a field/value or field/regex pair, quote is optional defaults to True")


    def get_fields(self, fields):
        '''
        Gets a list of fields for the query of a set of records.  Defaults to _key,title if nothing valid is passed
        To get all fields pass any, all or * in fields as a string
        '''
        if fields is None:
            return ["_key", "title"]
        elif str(fields).lower() in ["*", "all", "any"]:
            return []
        else:
            return fields
