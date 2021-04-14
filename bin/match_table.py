#!/usr/bin/env python
# coding=utf-8
#

import re
import logging

class MatchTable(object):
    """
    """
    def __init__(self, cols):
        self._rows = []
        self.logger = logging.Logger.manager.getLogger(self.__class__.__name__)
        #self.prio_rows = {}
        self.cols = cols

    def len(self):
        return len(self._rows)

    def add_row(self, row):
        self._add_match_row(MatchRow(row, cols=self.cols, ordinal=len(self._rows)))

    def _add_match_row(self, match_row, prio=0, colname=None):
        # storig these as tuples, in the initial load they are 0 because we don't ko wthe
        self._rows.append(match_row) #, prio, colname))

    # gets a dict of key/value pairs for this row from the lookup
    def get_row(self, pos):
        return self._rows[pos].get_values()

    def match_table(self, record):
        """
        search for all items im cols find the matching rows from dict
        params:
        cols: list of column names
        record: a splunk event to match to the table

        returns a single dict that was the best match for the input passed
        if nothing matches we return None
        """
        # find the matching rows
        info = self.logger.info
        self.logger.debug("match table cols:{} record:{}".format(self.cols, record))
        tbl = self
        try:
            for col in self.cols:
                tbl = tbl._match(col, record[col])
                if tbl.len() == 0:
                    # nothing left to do ... we didn't match
                    info("match table has no rows to return")
                    return None
        except KeyError:
            # key doesn't exist in message is a failed match
            self.logger.warn("Key(s) '{}' doesn't exist in input message {}".format(str(self.cols), record))
            return None

        tbl.drop_low_prio_rows()

        return tbl.get_first_row().get_values()

    def get_first_row(self):
        # if more than 1 remain take the one that was inserted first
        if self.len() > 1:
            self._rows.sort(key=lambda t: t.idx)
        elif self.len() == 0:
            self.logger.warn("match table is empty return empty dictionary")
            return {}

        return self._rows[0]


    def drop_low_prio_rows(self):
        # prune the rows down based on prioirty rules
        # for each column, in order, drop any rows that are not equal to the highest priority
        for col in self.cols:
            if self.len() == 1:
                # we are done when there is just 1 left
                self.logger.info("matched table 1 row remains")
                return
            self.prune_rows(col)

    def prune_rows(self, colname):
        """
        By this stage the table should contain just the rows that matched the input data
        Go through and discard and rows that have low match priority
        we do this by scoring rows using this - 10^(priority^2) * (length-1)
        * is always 1
        """
        rows = []
        for row in self._rows:
            cell = row.get_value(colname)
            importance = pow(cell.prio, 2) * (0 if cell.is_any_match() else cell.length)
            rows.append((row, pow(10, importance)))
        self.logger.debug("prune rows, colname={}, row_count={}".format(colname, len(rows)))
        rows.sort(key=lambda t: t[1], reverse = True)
        # now max prio row is at the head of this list
        max = rows[0][1]
        self._rows = []
        while len(rows) > 0 and rows[0][1] == max:
            row = rows.pop(0)[0]
            self.logger.debug("prune is adding row {}".format(row.get_values()))
            self._add_match_row(row)


    def _match(self, colname, value):
        """
        find all rows where the column matches and return a new table
        """
        new_table = MatchTable(self.cols)
        self.logger.debug("Matching {} to {}".format(colname, value))
        for row in self._rows:
            matched = row.match_row(colname, value)
            if matched[0]:
                new_table._add_match_row(row)
        return new_table


class MatchRow(object):
    def __init__(self, row, cols, ordinal=1):
        """
        odict is OrderedDict
        ordinal
        """
        self.logger = logging.Logger.manager.getLogger(self.__class__.__name__)
        self.idx = ordinal  # will be used to select the highest priority row if all fields match
        self._row = {}
        self._orig_row = row
        self.logger.debug("Creating Match Row {}".format(row))
        for k, v in row.iteritems():
            if k in cols:
                self._row[k] = MatchValue(k, v)

    def get_value(self, col):
        '''
        get a single value based on the column name
        '''
        return self._row[col]

    def get_values(self):
        """
        get all values as a dict
        """
        return self._orig_row
        '''
        r = {}
        for k, v in self._row.iteritems():
            r[k] = v.get_value()
        return r        
        '''

    def match_row(self, col, value):
        """
        Does value match the cell named by col in this row?
        """
        try:
            return self._row[col].match_value(value)
        except KeyError: # col doesn't exist, quietly fail, log an error ... maybe
            return (False,0, 0)

class MatchValue(object):
    """
    Represents a single value in a row
    """
    def __init__(self, k, v):
        """
        params:
        k - is the key field, ie column name
        v - is the value to match
        """
        self.logger = logging.Logger.manager.getLogger(self.__class__.__name__)
        self._key = k
        self._value = v
        self.prio = 2  # higher the number the higher the priority of the match
                       # 0=any, 1=contains, 2=start/ends with (default) , 3=equals
        # len is used to determine the highest priority match when two rows are the same
        self.length = len(v)
        # build a string for the regex
        if v == "*":
            # is a lone star so matches everything
            self._pattern = False
            self.prio = 0
            self.length = 0
        else:
            first_char = v[:1]
            last_char = v[-1:]
            if first_char == "*":
                if last_char != "*":
                    # ends-with, strip the leading *
                    self._func = self._endswith
                    self._pattern = v[1:]
                else:
                    # it is contains *abc*, strip leading and training *
                    self._pattern = v[1:-1]
                    self.prio = 1
                    self._func = self._contains
            elif last_char == "*":
                #  starts-with strip the trailing *
                self._pattern = v[:-1]
                self._func = self._startswith
            else:
                # its an exact match so abc becomes ^abc$
                self._pattern = v
                self.prio = 3
                self._func = self._equals
            self.length = len(self._pattern)

    def _contains(self, other):
        return self._pattern in other

    def _startswith(self, other):
        return other.startswith(self._pattern)

    def _endswith(self, other):
        return other.endswith(self._pattern)

    def _equals(self, other):
        return other == self._pattern

    def match_value(self, str):
        if not self._pattern:
            match = True # no pattern means match all
        else:
            match = bool(self._func.__call__(str))
        #self.logger.info("Match Value {} to {}".format(str, self._pattern))
        return (match, self.prio, self.length)

    def get_value(self):
        return self._value

    def is_any_match(self):
        return not bool(self._pattern)

class MatchValueRex(object):
    """
    Represents a single value in a row
    """
    def __init__(self, k, v):
        """
        params:
        k - is the key field, ie column name
        v - is the value and could potentially be a match string as shown below as
        one of match, starts-with, ends with or contains
        eg:
            abc    exact match  ==> ^abc$
            abc*   starts with  ==> ^abc
            *abc   ends with    ==> abc$
            abc    contains     ==> abc
        """
        self.logger = logging.Logger.manager.getLogger(self.__class__.__name__)
        self._key = k
        self._value = v
        self.prio = 2  # higher the number the higher the priority of the match
                       # 0=any, 1=contains, 2=start/ends with (default) , 3=equals
        # len is used to determine the highest priority match when two rows are the same
        self.length = len(v)
        # build a string for the regex
        if v == "*":
            # is a lone star so matches everything
            self._rex = False
            self.prio = 0
        else:
            # need to build a regex for it
            pattern = v
            first_char = v[:1]
            last_char = v[-1:]
            if first_char == "*":
                if last_char != "*":
                    # ends-with, ie *abc becomes abc$
                    pattern = v[1:]+"$"
                else:
                    # it is contains *abc* becomes abc
                    pattern = v[1:-1]
                    self.prio = 1
            elif last_char == "*":
                #  starts-with ie abc* becomes ^abc, strip the trailing *
                pattern = "^"+v[:-1]
            else:
                # its an exact match so abc becomes ^abc$
                pattern = "^{}$".format(v)
                self.prio = 3
            self._pattern = pattern
            self.logger.info("rex is '{}'".format(pattern))
            self._rex = re.compile(pattern)

    def match_value(self, str):
        if not self._rex:
            match = True # no regex seen means match all
        else:
            match = bool(self._rex.search(str))
        return (match, self.prio, self.length)

    def get_value(self):
        return self._value