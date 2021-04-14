
import time

class Perf(object):
    def __init__(self, logger):
        self.timers = {}
        self.logger = logger

    def start(self, str):
        self.timers[str] = {"s":time.time()}

    def end(self, str, context=""):
        ctx = ""
        exec_t = time.time() - self.timers[str]["s"]
        if len(context) > 0:
            ctx = ", context:{}".format(context)
        self.logger.info("Perf Job {} completed in {}{}".format(str, exec_t, ctx))
        return exec_t