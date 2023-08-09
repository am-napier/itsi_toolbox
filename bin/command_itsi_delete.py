#!/usr/bin/env python
# coding=utf-8
#
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import splunklib

import json
import time

@Configuration()
class ItsiDeleteCommand(GeneratingCommand):


    opt_confirm = Option(
        doc='''
        **Syntax:** **confirm=***boolean*
        **Description:** If true then run the delete, if false or null then just count the affected objects for the given filter.
        **Default:** False''',
        name='confirm',
        require=False,
        default=False,
        validate=validators.Boolean())    

    opt_type = Option(
        doc='''
        **Syntax:** **type=***entity|service|kpi_threshold_template|deepdive*
        **Description:** String value from the REST endpoint itoa_interface/get_supported_object_types
        **Default:** None''',
        name='type',
        require=True,
        default=None,
        validate=validators.Set("team", "entity", "service", "base_service_template", "kpi_base_search", "deep_dive", "glass_table", "home_view", "kpi_template", 
                "kpi_threshold_template", "event_management_state", "entity_relationship", "entity_relationship_rule", "entity_filter_rule", "entity_type"))    

    opt_field = Option(
        doc='''
        **Syntax:** **field=****string*
        **Description:** A property to search, eg title or host
        **Default:** title''',
        name='field',
        require=False,
        default='title',
        validate=validators.Fieldname())  

    opt_pattern = Option(
        doc='''
        **Syntax:** **pattern=****regex*
        **Description:** An unanchored regex string to search with, ie a value of 'A' matches everything that contains an A
                         Will reject an empty string with value error
        **Default:** None''',
        name='pattern',
        require=True)  

    def __init__(self):
        super(ItsiDeleteCommand, self).__init__()


    def generate(self):
        '''
        '''
        self.logger.debug(f'Generating command to delete ITSI Object Type:{self.opt_type} confirm:{self.opt_confirm} pattern:{self.opt_pattern}, field:{self.opt_field}')
        '''
        Deletes kvstore records using a filter or checks to see how many will be deleted

        filter='{"title": {"$regex":"(od|eve).*"}}'  
        '''
        result = {}
        msg = None
        if self.opt_pattern is None or self.opt_pattern=="":
            raise ValueError("ERROR: no value for pattern was passed or its blank")

        object_filter = f'{{"{self.opt_field}": {{"$regex":"{self.opt_pattern}"}}}}'
        # create the URL
        url = f"/servicesNS/nobody/SA-ITOA/itoa_interface/{self.opt_type}"
        self.logger.info(f"{self.opt_type} delete by filter confirm:{self.opt_confirm} filter={object_filter} url={url}")
                
        if not self.opt_confirm:
            # calls the url as a get - ie NO delete
            res = self.get_context().get(url, filter=object_filter)
            n_objs = len(json.loads(res['body'].read()))
            msg = f"DEBUG - command will delete {n_objs} {self.opt_type}(s) when run with confirm=1."
        else:
            # calls the url using HTTP - DELETE
            res = self.get_context().delete(url, filter=object_filter)
            if int(res['status']) > 299:
                msg = f"ERROR during entity delete {res['status']}, check logs."
                self.logger.error(json.dumps(res))
            else:
                msg = f"ITSI Object delete OK status:{res['status']}"
        
        result['_raw'] = msg
        result['filter'] = object_filter
        result['url'] = url
        result['http_status'] = res['status']
            
        self.logout()    
        yield result
        

    def get_context(self):
        '''
        logging into localhost therefore this expects to be running on an itsi searchhead with kvstore local
        '''
        if not hasattr(self, 'context'):
            self.logger.debug("delitsi prepare, creating context")
            self.context = splunklib.binding.connect(token=self.service.token, host="localhost", port=8089)

        return self.context


    def logout(self):
        '''
        logout if it was logged in
        '''
        if hasattr(self, 'context'):
            self.context.logout()



if __name__ == '__main__':
    dispatch(ItsiDeleteCommand, module_name=__name__)