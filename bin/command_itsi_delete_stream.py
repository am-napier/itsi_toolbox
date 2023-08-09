#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib

import json
import time

@Configuration()
class ItsiDeleteCommand(StreamingCommand):

    """
    Option not supported by the REST API so commented for now
    opt_batch_size = Option(
        doc='''
        **Syntax:** **batch_size=***int*
        **Description:** Number of objects to delete per operation.
        **Default:** 100''',
        name='batch_size',
        require=False,
        default=100,
        validate=validators.Integer())

    opt_timeout = Option(
        doc='''
        **Syntax:** **timeout=***int*
        **Description:** Number of minutes to let this go on for.
        **Default:** 10''',
        name='timeout',
        require=False,
        default=10,
        validate=validators.Integer())
    """

    opt_debug = Option(
        doc='''
        **Syntax:** **debug=***boolean*
        **Description:** If true then just test the delete
        **Default:** False''',
        name='debug',
        require=False,
        default=True,
        validate=validators.Boolean())

    opt_mode = Option(
        doc='''
        **Syntax:** **mode=***string*
        **Description:** Either id or filter, if id then each row must conatin a valid object ID.  If filter then expects a column called filter
        with a key=value format, ie filter="dc=ACME" will delete all entities that have an attribute dc matching the regex ^ACME$
        **Default:** id''',
        name='mode',
        require=False,
        default="id",
        validate=validators.Set("id", "filter"))

    opt_is_rex = Option(
        doc='''
        **Syntax:** **is_rex=***boolean*
        **Description:** If true then the value component of the field will be used as a regex term, ie filter="villan=wile|sam" yields matches for all villans
        whos names contain wile or same
        **Default:** False''',
        name='is_rex',
        require=False,
        default=False,
        validate=validators.Boolean())

    opt_type = Option(
        doc='''
        **Syntax:** **type=***entity|service|kpi_threshold_template|deepdive*
        **Description:** String value from the REST endpoint itoa_interface/get_supported_object_types
        **Default:** entity''',
        name='type',
        require=True,
        validate=validators.Set("team", "entity", "service", "base_service_template", "kpi_base_search", "deep_dive", "glass_table", "home_view", "kpi_template", 
                "kpi_threshold_template", "event_management_state", "entity_relationship", "entity_relationship_rule", "entity_filter_rule", "entity_type"))    


    def __init__(self):
        super(ItsiDeleteCommand, self).__init__()


    def stream(self, records):
        '''
        Called from the search pipeline to delete object sfrom the itsi kvstore collections
        Can delete any object that is a valid object type
        Deletes can be done by ID or by filter
        Use the debug mode to check what the filter matches
        '''
        t1 = time.time()
        n = 0
        for record in records:
            n = n+1
            self.logger.debug('Record to delete ITSI Objects: '.format(record))
            t2 = time.time()
            if self.opt_mode == "id":
                self.delete_by_id(record)
            else:
                self.delete_by_filter(record)
            t3 = time.time()
            self.logger.debug("single_delete_time={}".format(t3-t2))
            yield record
        t4 = time.time()
        if n > 0:
            self.logger.info("total_delete_time={}".format(t4 - t1))
        
        self.logout()


    def get_context(self):
        '''
        logging into localhost therefore this expects to be running on an itsi searchhead with kvstore local
        '''
        if not hasattr(self, 'context'):
            self.logger.debug("delitsi prepare, creating context")
            self.context = splunklib.binding.connect(token=self.service.token, host="localhost", port=8089)

        return self.context


    def logout(self):
        '''
        logout if it was logged in
        '''
        if hasattr(self, 'context'):
            self.context.logout()


    def delete_by_id(self, record):
        '''
        Deletes records one row at a time using the kvstore key field
        '''
        entity_id=record.get("id", "None")
        self.logger.info("called delete_by_id:{}".format(entity_id))
        url = f"/servicesNS/nobody/SA-ITOA/itoa_interface/{self.opt_type}/{entity_id}"
        if self.opt_debug:
            msg = f"noop - this is debug: {url}"
        else:
            res = self.get_context().delete(url)
            self.logger.info("Delete Response status:{}, ".format(res['status']))
            msg = res['status']
        record['delete response'] = msg


    def delete_by_filter(self, record):
        '''
        Deletes kvstore records using a filter or checks to see how many will be deleted
        Caller may specify if this is regex or not
        filter='{"title": "foo"}'
          or
        filter='{"type": {"$regex":"(od|eve).*"}}  "^[^ABC]$"
        '''
        filter = record.get("filter")
        if filter is None or filter=="":
            record['delete response'] = "no filter string was passed"
        else:
            # create the filter
            key, value = [i for i in filter.split("=", 1)]
            if len(value)==0:
                msg = f"Can't pass an empty value in the filter:'{filter}', to delete empty strings explictity use a regex like ^$"
            else:
                value = f'"{value}"'
                if self.opt_is_rex: #
                    value = f'{{"$regex": {value}}}'
                object_filter = f'{{"{key}": {value}}}'
                record['delete.filter'] = object_filter
                # create the URL
                url = f"/servicesNS/nobody/SA-ITOA/itoa_interface/{self.opt_type}"
                self.logger.info(f"{self.opt_type} delete by filter debug={self.opt_debug} filter={object_filter} url={url}")
                
                if self.opt_debug:
                    # calls the url as a get - ie NO delete
                    res = self.get_context().get(url, filter=object_filter)
                    msg = f"noop: this is debug only, action will delete {len(json.loads(res['body'].read()))} {self.opt_type} objects when run"
                    record['url'] = url
                    record['filter'] = filter
                else:
                    self.logger.info(f"Entity delete filter is {object_filter}")
                    # calls the url using HTTP - DELETE
                    res = self.get_context().delete(url, filter=object_filter)
                    if int(res['status']) > 299:
                        msg = "Error during entity delete {}".format(res['status'])
                        
                    else:
                        msg = f"ITSI Object delete OK status:{res['status']}"            
            record['delete.response'] = msg
        self.logger.info("Delete Response status:{}, ".format(record))


if __name__ == '__main__':
    dispatch(ItsiDeleteCommand, module_name=__name__)