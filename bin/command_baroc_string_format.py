#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
from baroc_string_format import BarocStringFormat

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'searchcommands_app', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class BarocStringFormatCommand(StreamingCommand):

    debug = Option(require=False, name="debug", default="0")
    input_field = Option(require=False, name="input_field", default="template")
    output_field = Option(require=False, name="output_field", default="ops_msg")

    def normalize_debug(self, debug):
        return debug.lower() in ['true', '1', 't', 'y', 'yes']

    def stream(self, records, format_field="template", output_field="ops_msg", debug=0):

        if self.input_field:
            format_field = self.input_field
        if self.output_field:
            output_field = self.output_field
        if self.debug:
            debug = self.normalize_debug(self.debug)

        baroc_string_format = BarocStringFormat()
        for record in records:
            try:
                input_template = record[format_field]
                record[output_field] = baroc_string_format.string_template(input_template, record)
                if debug:
                    record['debug'] = baroc_string_format.debug_msg
                self.logger.debug("BarocStringFormatCommand input_template=[%s] ops_msg=[%s]" % (
                input_template, record[output_field]))
            except KeyError as err:
                self.logger.error("KeyError missing key={} in record={}".format(err, record))
            yield record

 
dispatch(BarocStringFormatCommand, sys.argv, sys.stdin, sys.stdout, __name__)
