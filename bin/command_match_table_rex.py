#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import time, re

@Configuration()
class MatchupCommandRex(StreamingCommand):
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

    opt_regex = Option(
        doc='''
        **Syntax:** **regex=***<regex field in lookup>*
        **Description:** Names the field in the lookup that stores the regex.
        **Default:** none''',
        name='regex',
        require=True)

    opt_field = Option(
        doc='''
        **Syntax:** **field=***<field to match>*
        **Description:** Names the field in the event that is matched to the regex.
        **Default:** none''',
        name='field',
        require=True)

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

    opt_sort = Option(doc='''
        **Syntax:** **sort=***<string>*
        **Description:** SPL style sort string, ie '- order'
        **Default:** empty string''',
        name='sort',
        default=None,
        require=False)

    opt_undefined_str = Option(doc='''
        **Syntax:** **undefined=***<string>*
        **Description:** string to use if the column doesn't exist in the output
        **Default:** undefined''',
        name='undefined',
        default='undefined',
        require=False)

    table = None

    def __init__(self):
        super(MatchupCommandRex, self).__init__()
        self.perf = Perf(self.logger)

    def get_where_clause(self):
        where = self.opt_where
        self.logger.info("option where is (%s)" % where)
        if where is not None:
            return " WHERE " + where
        return ""

    def get_sort_clause(self):
        sort = ""
        if self.opt_sort is not None:
            sort = " | sort "+self.opt_sort
            self.logger.info("option sort is (%s)" % sort)
        else:
            self.logger.info("option sort is empty")
        return sort

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
                                    "search": "| inputlookup {} {} {}".format(self.opt_lookup, self.get_where_clause(), self.get_sort_clause())
                                })
            table = MatchTableRex(self.opt_regex, self.logger)
            res.raise_for_status()
            for line in res.text.strip().split("\n"):
                table.add_row(json.loads(line)["result"])
                self.logger.info("Line is {}".format(line))
            self.perf.end("get_table_raw", "%d Rows"%table.len())
            self.table = table
        return self.table


    def stream(self, records):
        """
        Main entry point for the command
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
            match = tbl.get_match(self.opt_field, record)
            if match is not None:
                for col in self.opt_outputcols:
                    try:
                        record[col] = match[col]
                    except KeyError:
                        record[col] = self.opt_undefined_str
            else:
                self.logger.warn("No match for row {}".format(record))
                record["debug"] = "nothing matched this record"
            self.perf.end(perf_str)
            yield record

        self.logger.info("Iterated over {} records".format(sz))
        self.perf.end("full stream method", "{} events processed".format(sz))

class MatchTableRex(object):
    def __init__(self, regex_field, logger):
        self.regex_field = regex_field
        self.rows = []
        self.output_cols = []# self.opt_outputcols.split(",")
        self.logger = logger

    def add_row(self, row):
        self.logger.info("QWERTY Adding Row")
        self.rows.append((re.compile(row[self.regex_field]), row))

    def get_match(self, field, record):
        """
        loop over all rows in the table and check if rex in the row matches the record[field_name]
        """
        self.logger.info("QWERTY IN GET MATCH")
        value = record[field]
        for rex, row in self.rows:
            self.logger.info("QWERTY IN GET MATCH ROW rex:{} row{}".format(rex, row))
            if rex.search(value):
                self.logger.info("QWERTY MATCHED IN GET MATCH ROW rex:{} row{}".format(rex, row))
                return row
        self.logger.info("QWERTY NO MATCHED".format())
        return None


    def len(self):
        return len(self.rows)

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
    dispatch(MatchupCommandRex, module_name=__name__)
