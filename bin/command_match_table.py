#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators, environment
import splunklib.results as results
from match_table import MatchTable
from baroc_string_format import BarocStringFormat
import time

import json
import time
import urllib
import sys, traceback

@Configuration()
class MatchupCommand(StreamingCommand):
    """
    SCP v2
    """
    
    opt_outputcols = Option(
        doc='''
        **Syntax:** **outputcols=***<CSV list of fields>*
        **Description:** The field(s) that should be returned from the table.
        **Default:** <empty> returns all fields''',
        name='outputcols',
        require=False,
        default='',
        validate=validators.List())

    opt_inputcols = Option(
        doc='''
        **Syntax:** **inputcols=***<CSV list of key fields to match>*
        **Description:** Each field in keys is matched with the lookup using the rules defined for matchup, this does not work like lookup, read the docs.
        **Default:** none''',
        name='inputcols',
        require=True,
        validate=validators.List())

    opt_lookup = Option(
        doc='''
        **Syntax:** **lookup=***<lookup_name>*
        **Description:** name of a valid accessible lookup
        **Default:** none''',
        name='lookup',
        require=True
    )

    opt_where = Option(
        doc='''
        **Syntax:** **where=***<valid where clause>*
        **Description:** where clause that can be used with inputlookup to restrict the rows returned and improve performance
        **Default:** none''',
        name='where',
        default=None,
        require=False
    )

    opt_undefined_str = Option(doc='''
        **Syntax:** **undefined=***<string>*
        **Description:** string to use if the column doesn't exist in the output
        **Default:** undefined''',
        name='undefined',
        default='undefined',
        require=False)

    opt_debug = Option(
        doc='''
            **Syntax:** **debug=***<boolean>*
            **Description:** Wether the command should populate a error messege in a dubug field. 
            **Default:** none''',
        name='debug',
        default='False',
        require=False
    )

    table = None

    def __init__(self):
        super(MatchupCommand, self).__init__()
        self.perf = Perf(self.logger)
        self.barocstringformat = BarocStringFormat()

    def normalize_debug(self, debug):
        return debug.lower() in ['true', '1', 't', 'y', 'yes']

    def get_where_clause(self):
        where = self.opt_where
        self.logger.info("option where is (%s)" % where)
        if where is not None:
            return " WHERE " + where
        return ""

    def get_table_slow_with_splunklib(self, force=False):
        """
        Here we'll add the code to fetch the lookup, once only ...
        Not pretending this isan awesome super scalable solution so for now we just read the whole file.
        Would be nice if we could use some static memory to store it as well, need FDSE/Eng input for that job though
        """
        if self.table == None:
            self.perf.start("load table")
            self.logger.info("================== Live call starting")

            search = "| inputlookup {} {} ".format(self.opt_lookup, self.get_where_clause())
            self.logger.info("Lookup search is : {}".format(search))
            self.perf.start("rest call")
            self.logger.info("FARK : {}".format(self._metadata))

            res = self.service.jobs.oneshot(search, **{"count":0})
            self.perf.end("rest call")
            # Get the results and display them using the ResultsReader
            reader = results.ResultsReader(res)
            self.table = MatchTable(self.opt_inputcols)
            self.perf.end("rest call", "part 2")
            rows = []
            i = 0
            for row in reader:
                #rows[i] = row
                #i = i+1
                pass

            self.perf.end("load table", "table size: "+str(self.table.len()))

        return self.table

    def get_table_fast_and_raw(self):
        if self.table is None:
            import requests, json
            self.perf.start("get_table_raw")

            res = requests.post("%s/services/search/jobs/export" % (self.metadata.searchinfo.splunkd_uri), verify=False,
                                headers={
                                    "Authorization": "Splunk %s" % self.metadata.searchinfo.session_key,
                                    "Accept-Encoding": "gzip,deflate",
                                    "User-Agent": "Python Requests",
                                    "Content-Type": "application/json; charset=UTF-8",
                                    "Accept": "application/json"
                                },
                                data={
                                    "exec_mode": "oneshot",
                                    "output_mode": "json",
                                    "search": "| inputlookup {} {} ".format(self.opt_lookup, self.get_where_clause())
                                })
            table = MatchTable(self.opt_inputcols)
            res.raise_for_status()
            for line in res.text.strip().split("\n"):
                table.add_row(json.loads(line)["result"])
            self.perf.end("get_table_raw", "%d Rows"%table.len())
            self.table = table
        return self.table


    def map_to_output_colums(self, match, record, debug='False'):
        if self.opt_debug:
            debug = self.normalize_debug(self.opt_debug)

        if match is not None:
            for col in self.opt_outputcols:
                try:
                    record[col] = self.barocstringformat.string_template(match[col], record)
                    if debug:
                        record['debug'] = self.barocstringformat.debug_msg
                except KeyError:
                    record[col] = self.opt_undefined_str
        else:
            self.logger.warn("No match for row {}".format(record))
            record["debug"] = "nothing matched this record"
        return record

    def stream(self, records):
        """
        :param records: An iterable stream of events from the command pipeline.
        :return: `None`.
        """
        self.logger.info("================== Stream")
        sz = 0
        self.perf.start("full stream method")
        for record in records:
            sz += 1
            perf_str = "checking row {}".format(sz)
            tbl = self.get_table_fast_and_raw()
            self.perf.start(perf_str)
            match = tbl.match_table(record)
            record = self.map_to_output_colums(match, record)
            self.perf.end(perf_str)
            yield record

        self.logger.info("Iterated over {} records".format(sz))
        self.perf.end("full stream method", "{} events processed".format(sz))


class Perf(object):
    def __init__(self, logger):
        self.timers = {}
        self.logger = logger

    def start(self, str):
        self.timers[str] = {"s":time.time()}

    def end(self, str, context=""):
        ctx = ""
        if len(context) > 0:
            ctx = ", context:{}".format(context)
        self.logger.info("Perf Job {} completed in {}{}".format(str, time.time() - self.timers[str]["s"], ctx))

if __name__ == '__main__':
    dispatch(MatchupCommand, module_name=__name__)