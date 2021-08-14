#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import json

def get_bool(b):
    return str(b).lower() in ["true", "t", 1, "yes", "ok"]

@Configuration()
class TableOutputCommand(StreamingCommand):
    """

    """

    opt_fields = Option(
        doc='''
        **Syntax:** **fields=***string*
        **Description:** CSV list of fields to print
        **Default:** value''',
        name='fields',
        require=True,
        default="value")

    opt_output = Option(
        doc='''
        **Syntax:** **output=***string*
        **Description:** Name of the field we want to write to
        **Default:** mydescription''',
        name='output',
        require=False,
        default="mydescription",
        validate=validators.Fieldname())

    opt_header = Option(
        doc='''
        **Syntax:** **header=***string*
        **Description:** String to print as a header
        **Default:** None''',
        name='header',
        require=False,
        default=None)

    opt_footer = Option(
        doc='''
        **Syntax:** **fields=***string*
        **Description:** Footer to print
        **Default:** None''',
        name='footer',
        require=False,
        default=None)

    opt_separator = Option(
        doc='''
        **Syntax:** **separator=***string*
        **Description:** line of text to break the output
        **Default:** --------------------------''',
        name='separator',
        require=False,
        default="--------------------------")

    def __init__(self):
        super(TableOutputCommand, self).__init__()

    def stream(self, rows):
        fields = str(self.opt_fields).split(",")
        output = [] if self.opt_header is None else [self.opt_header]
        if self.opt_separator is not None:
            output.append(self.opt_separator)
        for row in rows:
            for field in fields:
                output.append(row[field])

            if self.opt_separator is not None:
                output.append(self.opt_separator)
            if self.opt_footer is not None:
                output.append(self.opt_footer)
            row[self.opt_output] = "\n".join(output)
            yield row


if __name__ == '__main__':
    dispatch(TableOutputCommand, module_name=__name__)

