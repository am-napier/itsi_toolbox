#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.client import Endpoint

import json
import time
import copy
from perf import Perf


DEF_FIELDS = "time_variate_thresholds,adaptive_thresholds_is_enabled,adaptive_thresholding_training_window," \
           "kpi_threshold_template_id,tz_offset"

def get_bool(b):
    return str(b).lower in ["true", "t", 1, "yes", "ok", "indeed-illy do!"]

@Configuration()
class AdaptiveThresholdCommand(StreamingCommand):
    """
        Set the adaptive threshold re-calculation to either on or off
        Allows the linking/unlinking of the threshold template
        What happens with the service template link ?-O
        Can we do this on the template too?  Seems to be the same set of properties
    """
    opt_mode = Option(
        doc='''
        **Syntax:** **mode=***string*
        **Description:** one of read, write or thresholds coming
        **Default:** read''',
        name='mode',
        require=False,
        default="read")

    opt_format = Option(
        doc='''
        **Syntax:** **format=***string*
        **Description:** applies to mode=read, Determines output from the command.  Specify either flat or json
        **Default:** json''',
        name='format',
        require=False,
        default="json")


    opt_fields = Option(
        doc='''
        **Syntax:** **fields=***string*
        **Description:** applies to mode=read, CSV list of fields to return
        **Default:** time_variate_thresholds,adaptive_thresholds_is_enabled,adaptive_thresholding_training_window,"
                "kpi_threshold_template_id,tz_offset''',
        name='fields',
        require=False,
        default=DEF_FIELDS)

    # region Command implementation
    def __init__(self):
        super(AdaptiveThresholdCommand, self).__init__()


    def prepare(self):
        pass

    def stream(self, records):
        """
        Process all events.
        :param records: An iterable stream of events from the command pipeline.
        :return: `None`.

        read: eval service_id=xxx kpi_id=yyy | adaptivethresholds format=<flat|json> mode=read [fields="adaptive_thresholds_is_enabled"]
        write: eval service_id=xxx kpi_id=yyy enabled=<true|false> | adaptivethresholds mode=write

        time_variate_thresholds
        adaptive_thresholds_is_enabled
        adaptive_thresholding_training_window
        kpi_threshold_template_id
        title
        _key

        First get a copy of the service config.  We have to change just a part but partial updates do not work on
        attributes that are 2nd or greater level deep so the whole JSON block must be writen back.

        """
        self.logger.info('ToggleAdaptiveThreshold Entering stream.')
        t1 = time.time()
        mode = self.opt_mode.lower()
        is_write = mode == "write"
        is_read = mode == "read"
        is_reset = mode == "reset"

        if not (is_read or is_write or is_reset):
            self.logger.error("unsupported mode, only read or write supported")
            return

        # Put your event transformation code here
        helper = AdaptiveThresholdHelper(self)
        for record in records:
            # delete this before production
            self.logger.info('Stream Record {0}'.format(record))
            t2 = time.time()
            service_id = record.get('service_id')
            kpi_id = record.get('kpi_id')

            if is_read:
                helper.do_read(service_id, kpi_id, record)
            elif is_write:
                helper.do_update(service_id, kpi_id, record)
            elif is_reset:
                helper.do_reset(service_id, kpi_id, record)

            self.logger.info("{} complete in {} secs".format(mode, time.time()-t2))
            yield record
        if is_write or is_reset:
            helper.write_cache()
        self.logger.info("Full update time is:{}".format(time.time() - t1))

    # endregion

class AdaptiveThresholdHelper(object):

    def __init__(self, command):
        self._svc_map = {}
        self.endpoint = Endpoint(command.service, '/servicesNS/nobody/SA-ITOA/itoa_interface/vLatest/service')
        self.logger = command.logger
        self.opt_mode = command.opt_mode
        self.opt_format = command.opt_format
        self.opt_fields = command.opt_fields


    def do_read(self, service_id, kpi_id, record):
        '''
        read the config strip the key attributes and add them to record then return
        '''
        svc = self.read_service(service_id)
        props = self.opt_fields.split(",")
        is_flat = self.opt_format == "flat"
        pre = "response." if is_flat else ""
        self.logger.info("DO READ: is_flat:{}, props:{}".format(is_flat,props))
        for kpi in svc['kpis']:
            if kpi['_key'] == kpi_id:
                self.logger.info("kpi found")
                resp = dict([(pre+p, kpi[p]) for p in props])

                if is_flat:
                    record.update(resp)
                else:
                    record['response'] = json.dumps(resp)
                break


    def do_update(self, service_id, kpi_id, record):
        enabled = get_bool(record.get('enabled', ""))
        '''
        for write we need to update adaptive_thresholds_is_enabled and since we are changing a template we unlink it 
        from kpi_thresholding_template_id.  Store the orig values for posterity and to allow a reset if needed.
        '''
        svc = self.read_service(service_id)
        for kpi in svc['kpis']:
            if kpi['_key'] == kpi_id:
                if not 'adaptive_orig_settings' in kpi:
                    # provide an undo state
                    kpi['adaptive_orig_settings'] = {
                        'adaptive_thresholds_is_enabled': kpi['adaptive_thresholds_is_enabled'],
                        'kpi_threshold_template_id': kpi['kpi_threshold_template_id']
                    }
                kpi['adaptive_thresholds_is_enabled'] = 1 if enabled else 0
                kpi['kpi_threshold_template_id'] = ''


    def do_reset(self, service_id, kpi_id, record):
        '''
        copy the values from the orig settings back, if they are there
        using pop also deletes the orig object
        '''
        svc = self.read_service(service_id)
        for kpi in svc['kpis']:
            if kpi['_key'] == kpi_id:
                kpi.update(kpi.pop('adaptive_orig_settings', {}))


    def write_cache(self):

        if len(self._svc_map) == 0:
            self.logger.info("Cache is empty, no writes to do.")
            return
        for id in self._svc_map:
            cfg = self._svc_map[id]
            query = {"body": json.dumps(cfg)}
            resp = self.endpoint.post(id, **query)
            if resp and resp['status'] > 299:
                self.logger.error("Failed writing service with id {} returned status {}".format(id))
                self.logger.error("Status {}".format(resp['status']))
                self.logger.error("Body {}".format(resp['body'].read()))
                raise Exception("write service failed, check logs")
            self.logger.info("update completed for svc:{} id:{}".format(cfg['title'], id))


    def read_service(self, svc):
        if svc in self._svc_map:
            self.logger.debug("read_service cache hit")
            return self._svc_map[svc]
        else:
            self.logger.debug("read_service cache miss")
            resp = self.endpoint.get(svc)
            if resp and resp['status'] < 300:
                self._svc_map[svc] = json.loads(resp['body'].read())
                return self._svc_map[svc]

        self.logger.error("Reading service with id {} returned status {}".format(svc, resp['status']))
        self.logger.error("Body {}".format(resp['body'].read()))
        raise Exception("read service failed, check logs")

if __name__ == '__main__':
    dispatch(AdaptiveThresholdCommand, module_name=__name__)