#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import json






@Configuration()
class PrettyPrintCommand(StreamingCommand):
    """
    Pretty print the JSON contents of one or more fields
    Can remove some of the fields from the target object if that helps reduce the size
    """
    opt_fields = Option(
        doc='''
        **Syntax:** **fields=***string*
        **Description:** CSV list of fields to print
        **Default:** value''',
        name='fields',
        require=True,
        default="value",
        validate=None) #validators.String())

    opt_remove = Option(
        doc='''
        **Syntax:** **fields=***string*
        **Description:** CSV list of fields to remove from the output
        **Default:** None''',
        name='remove',
        require=False,
        default=None,
        validate=None) #validators.Fieldname())

    opt_indent = Option(
        doc='''
        **Syntax:** **indent=***integer*
        **Description:** number of spaces to indent
        **Default:** 4''',
        name='indent',
        require=False,
        default=4,
        validate=validators.Integer())

    def __init__(self):
        super(PrettyPrintCommand, self).__init__()


    def stream(self, rows):
        self.logger.info('Prettyprint Command entering stream.')
        fields = str(self.opt_fields).split(",")
        rms = [] if self.opt_remove is None else str(self.opt_remove).split(",")
        self.logger.info('fields {}, remove: {}'.format(fields, rms))
        for row in rows:
            for field in fields:
                self.logger.info('field to print {}'.format(field))
                try:
                    obj = json.loads(row[field])
                    for rm in rms:
                        self.logger.info('removing {}'.format(rm))
                        obj.pop(rm, None)
                    row[field] = json.dumps(obj, indent=self.opt_indent)
                except KeyError as ke:
                    row[field] = "KeyError"
                except Exception as e:
                    row[field+"_error"] = str(e)
            yield row

if __name__ == '__main__':
    dispatch(PrettyPrintCommand, module_name=__name__)

