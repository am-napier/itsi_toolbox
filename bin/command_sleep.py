#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib

import json
import time
import math


from multiprocessing import Pool
from multiprocessing import cpu_count


_PAUSE=10
def _f(x):
    t=time.time()
    while True:
        x*x
        if time.time()-t > _PAUSE/1000:
            break


@Configuration()
class SleepCommand(StreamingCommand):

    """
    """
    opt_load = Option(
        doc='''
        **Syntax:** **load=***int*
        **Description:** Percetange of cores to load up with activity
        **Default:** 0''',
        name='load',
        require=False,
        default="0",
        validate=validators.Integer(minimum=0))

    opt_pause = Option(
        doc='''
        **Syntax:** **pause=***int*
        **Description:** number of milliseconds to block the pipe for
        **Default:** 1000''',
        name='pause',
        require=False,
        default=1000,
        validate=validators.Integer(minimum=1))


    def __init__(self):
        super(SleepCommand, self).__init__()
        #_PAUSE=18


    def stream(self, records):
        '''
        Pause the processing pipe for every message receieved, optionally burn some carbon in CPU cycles
        global cludge is get around pickling errors from multiprocessing
        '''
        global _PAUSE
        _PAUSE = self.opt_pause
        t1 = time.time()
        self.logger.info(f" Sleep period {_PAUSE} msecs")
        processes = max(1, math.floor(cpu_count()*self.opt_load/100))
        pool = Pool(processes)
        for record in records:    
            start = time.time()
            
            if self.opt_load == 0:
                self.logger.info("Sleep, no load")
                time.sleep(self.opt_pause/1000)
            else:
                self.logger.info("Sleep, with load {self.opt_load}")
                pool = Pool(processes)
                pool.map(_f, range(processes))
            end = time.time()
            record['started_at'] = start
            record['ended_at'] = end
            record['duration'] = end-start
            yield record

        self.logger.info(f"- ( ^ O ^ ) - ... {round(time.time()-t1, 3)}")

if __name__ == '__main__':
    dispatch(SleepCommand, module_name=__name__)