#!/usr/bin/env python
# coding=utf-8
#
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib

import json
import time
import math


from multiprocessing import Pool
from multiprocessing import cpu_count
import threading

import random
import string

_PAUSE=10

def _f(x):
    t=time.time()
    while True:
        x*x
        if time.time()-t > _PAUSE/1000:
            break

class DebugLogger():
    def __init__(self):
        pass

    def info(self, m):
        print(f"{time.strftime('%F %T', time.localtime())} {m}")

@Configuration()
class SleepCommand(StreamingCommand):

    """
    command to sleep the search pipe, may also be used to load the processor(s)
    pauses on every record so 10 events with a sleep command of pause=100 is ~ 1 sec
    I used this for testing the scheduler
    | makeresults | sleep [| makeresults | eval pause=random()%500+500 | fields pause ]
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

    opt_memory = Option(
        doc='''
        **Syntax:** **memory=***int*
        **Description:** minimum MB to waste, PER EVENT!.  Note that python doubles array sizes as it increases so this is the minimum amount wasted on each event processed
        **Default:** 0''',
        name='memory',
        require=False,
        default="0",
        validate=validators.Integer(minimum=0))

    opt_disk = Option(
        doc='''
        **Syntax:** **disk=***int*
        **Description:** number of 1kb fields to write into each event, see fields filler_n
        **Default:** 0''',
        name='disk',
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
        default=1,
        validate=validators.Integer(minimum=0))

 
    def __init__(self):
        super(SleepCommand, self).__init__()


    def stream(self, records):
        '''
        Pause the processing pipe for every message receieved, optionally burn some carbon in CPU cycles
        global cludge is get around pickling errors from multiprocessing
        '''
        global _PAUSE, wasted
        _PAUSE = self.opt_pause
        wasted = []
        #one_mb = [0] * 100000
        inc = [0] * (100000 * self.opt_memory)
        t1 = time.time()
        self.logger.info(f" Sleep period {self.opt_pause} msecs, CPU load @{self.opt_load}%, {self.opt_memory} MB wasted per event")
        processes = max(1, math.floor(cpu_count()*self.opt_load/100))

        mem_sz = self.opt_memory
        pool = Pool(processes)
        MB = 1048576 
        for record in records:    
            start = time.time()

            n=0
            while sys.getsizeof(wasted) < (mem_sz * MB):
                wasted = wasted + inc
                n=n+1


            if self.opt_disk > 0:
                for i in range(0, self.opt_disk):
                    record[f"filler_{i}"] = ''.join(random.choices(string.ascii_letters + string.digits, k=1000))


            self.logger.info(f'n={n}, wasted={round(sys.getsizeof(wasted)/MB, 2)} MB')
            mem_sz = mem_sz+self.opt_memory

            if self.opt_load == 0:
                time.sleep(self.opt_pause/1000)
            else:
                pool.map(_f, range(processes))

            end = time.time()
            record['started_at'] = start
            record['ended_at'] = end
            record['duration'] = end-start
            yield record


        self.logger.info(f"- ( ^ O ^ ) - ... {round(time.time()-t1, 3)}")
        #time.sleep(20)

if __name__ == '__main__':
    dispatch(SleepCommand, module_name=__name__)
