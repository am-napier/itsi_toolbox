#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib

import json
import time

@Configuration()
class DeleteObjectsCommand(StreamingCommand):

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

    opt_dry_run = Option(
        doc='''
        **Syntax:** **dry_run=***boolean*
        **Description:** If true then just test the delete
        **Default:** False''',
        name='dry_run',
        require=False,
        default=False,
        validate=validators.Boolean())

    opt_by_id = Option(
        doc='''
        **Syntax:** **by_id=***boolean*
        **Description:** If true then delete by id found in each row, false then delete using filter properties
        **Default:** True''',
        name='by_id',
        require=False,
        default=True,
        validate=validators.Boolean())

    opt_is_rex = Option(
        doc='''
        **Syntax:** **is_rex=***boolean*
        **Description:** If true then the field_value will be used as a regex term
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
        require=False,
        default="entity",
        
        validate=validators.Set())    


    def __init__(self):
        super(DeleteObjectsCommand, self).__init__()


    def prepare(self):
        """
        Not supported yet
        self.timeout = time.time() + int(self.opt_timeout) * 60
        self.logger.info("Ctor batch_size:{}, dry_run:{}, is_rex:{}, by_id:{}, timeout: {}".format(
            self.opt_batch_size, self.opt_dry_run, self.opt_is_rex, self.opt_by_id, self.timeout))
                """
        self.logger.info("Ctor dry_run:{}, is_rex:{}, by_id:{}".format(self.opt_dry_run, self.opt_is_rex, self.opt_by_id))

    def stream(self, records):
        t1 = time.time()
        n = 0
        for record in records:
            n = n+1
            self.logger.debug('Record to delete ITSI Objects: '.format(record))
            t2 = time.time()
            if self.opt_by_id:
                self.delete_by_id(record)
            else:
                #self.future_delete_by_filter(self.opt_is_rex, '''self.opt_batch_size,''' self.opt_dry_run, record)
                self.delete_by_filter(self.opt_is_rex, self.opt_dry_run, record)
            t3 = time.time()
            self.logger.debug("single_delete_time={}".format(t3-t2))
            yield record
        t4 = time.time()
        if n > 0:
            self.logger.info("total_delete_time={}".format(t4 - t1))
        self.context.logout()


    def get_context(self):
        if not hasattr(self, 'context'):
            self.logger.debug("delitsi prepare, creating context")
            self.context = splunklib.binding.connect(token=self.service.token, host="localhost", port=8089)

        return self.context


    def delete_by_id(self, record):
        entity_id=record.get("id", "None")
        self.logger.info("called delete_by_id:{}".format(entity_id))
        url = "/servicesNS/nobody/SA-ITOA/itoa_interface/%s/%s" % self.opt_type, entity_id
        res = self.get_context().delete(url)
        self.logger.info("Delete Response status:{}, ".format(res['status']))
        record['response'] = res['status']

    def delete_by_filter(self, is_rex, dry_run, record):
        '''
        filter='{"title": "foo"}'
          or
        filter='{"type": {"$regex":"(od|eve).*"}}
        '''
        key = record.get("filter_key", "KEY-NotSp3cIf13D")
        value = record.get("filter_value", "VALUE-NotSp3cIf13D")
        self.logger.info("delete by filter key: {}, value:{}, is_rex:{}".format(key, value, is_rex))
        value = '"%s"' % value
        if is_rex: #
            value = '{"$regex": %s}' % value
        object_filter = '{"%s": %s}' % (key, value)
        url = "/servicesNS/nobody/SA-ITOA/itoa_interface/%s" % self.opt_type
        if dry_run:
            res = self.get_context().get(url, filter=object_filter)
            record['filter-string'] = object_filter
            record['filter-response'] = res['status']
            record['filter-count'] = len(json.loads(res['body'].read()))
        else:
            self.logger.info("Entity delete filter is %s" % (object_filter))
            res = self.get_context().delete(url, filter=object_filter)
            if int(res['status']) > 299:
                record['filter-response'] = "Error during entity delete {}".format(res['status'])
                self.logger.error(record['filter-response'])
            else:
                record['filter-response'] = "ITSI Object delete OK status:{}".format(res['status'])
                self.logger.info(record['filter-response'])

        self.logger.info("Delete Response status:{}, ".format(record))


if __name__ == '__main__':
    dispatch(DeleteObjectsCommand, module_name=__name__)