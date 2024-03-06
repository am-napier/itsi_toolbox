#!/usr/bin/env python
# coding=utf-8
#
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.client import Endpoint

import json
import time
from itsi_kvstore import KVStoreHelper
import copy
from perf import Perf
import sys


@Configuration()
class MWCalCommand(StreamingCommand):
    """
    mwcal mode=list*|create|update|delete type=entity*|service title=<string> start=<epoch> duration=<mins> key=<guid>

    As an ITSI admin I want to manage my entire life using lookups becasue they rock
    This means I need to have the ability to create, update or delete maintenance windows in bulk from te serach bar
    So I want the option to 
    1. create/update 1 or more MW objects
    2. delete 1 or more MW objects
    3. list all my current MW objects - do that with a rest macro

    To create/update I expect to pass an event per MW to a search
    | makeresults count=3 | streamstats c | eval id="entity-".c | mwcal mode=create type=entity %5B| makeresults | eval start=_time | return start%5D duration=10 title=Foobah
    | makeresults | mwcal mode=delete title=foo

    | makeresults count=3 | streamstats c | eval id="entity-".c | mwcal mode=create type=entity 
      [| makeresults | eval start=_time | return start]
      duration=10 
      [| makeresults | eval start=_time | return start]

    | mwcal mode=update type=entity duration=10 key=<guid>

    """

    opt_mode = Option(
        doc='''
        **Syntax:** **mode=****string*
        **Description:** What are we doing upsert or delete?  upsert with an empty or unknown key
        perfroms a create/insert while a valid key runs an update.
        When updating not all args need to be provided as is_partial is used
        **Default:** None''',
        name='mode',
        require=True,
        default=None,
        validate=validators.Set("upsert", "delete"))

    """
    opt_type = Option(
        doc='''
        **Syntax:** **type=****string*
        **Description:** Default type, must be one of entity or service
        **Default:** entity''',
        name='type',
        require=False,
        default="entity",
        validate=validators.Set("entity", "service"))
    """
    
    opt_regex = Option(
        doc='''
        **Syntax:** **regex=****string*
        **Description:** regex is used for delete only
        **Default:** None''',
        name='regex',
        require=False,
        default=None)    
    
    """
    opt_start = Option(
        doc='''
        **Syntax:** **type=****integer*
        **Description:** Epoch start time, defaults to current system time
        **Default:** now ''',
        name='start',
        require=False,
        default=time.time(),
        validate=validators.Integer())

    opt_duration = Option(
        doc='''
        **Syntax:** **duration=****integer*
        **Description:** Default duration in minutes
        **Default:** 60''',
        name='duration',
        require=False,
        default=60,
        validate=validators.Integer())
    """   
    
 
    API = "maintenance_services_interface"
    TYPE = "maintenance_calendar"

    # region Command implementation
    def __init__(self):
        super(MWCalCommand, self).__init__()


    def stream(self, events):
        self.mw_kvstore = KVStoreHelper(self, object_type=self.TYPE, api=self.API)

        self.logger.info(f""" ---- MWCal stream ---- """)

        events = getattr(self, self.opt_mode)(events)
        for i in events:
            if "_key" in i:
                i["key"]=i["_key"] # expose it to the caller

            yield i

        
    def upsert(self, events):    
        """
        This is calling POST with a payload that can update or create the object
        Each event in events is a single update and the properties should be contained 
        in the event body as follows:
            key - the _key of the MW being changed (note if this doesn't exist it will be created)
            ids - mv field containing the ids to add to the MW
            type - is this for service or entity
            start - epoch start time for the MW
            duration - mins this MW is active
        """
        # validate we have a key then use the create body
        #if self.opt_type is None:
        #    raise ValueError("No type was passed, requires either entity or service")
        
        results = []
        for evt in events:
            
            start = int(evt.get('start', 0)) 
            duration = int(evt.get('duration', 0))
            end =  int(evt.get('end', -1)) 
            title = evt.get('title', None)
            key = evt.get('key', None)
            object_type = evt.get('type', None)

            if start == 0 or title is None or object_type is None:
                results.append({"status":"failed", 
                    "message" : f"Every event requires start:{start}, duration:{duration}, title:{title} and type:{object_type}."})
                continue

            if duration == 0 and end == -1:
                results.append({"status":"failed", 
                    "message" : f"Every event requires either a duration or end specified, set end=0 for infinite."})
                continue

            # caller asked for infinite window
            if end == 0:
                end = 2147385600

            if 'ids' in evt:
                # if there is just one id in the list it treats the string like a list so we wrapper it as a list
                ids = [evt['ids']] if isinstance(evt['ids'], str) else evt['ids']
            else:    
                results.append({"status":"failed", 
                    "message" : "Every event requires a list of ids, yes I know, even for updates"})
                continue
    
            end = end if end>-1 else start + duration*60

            payload = {
                'start_time' : start,
                'end_time' : end,
                'title' : title,
                'objects' : [{"_key": id, "object_type" : object_type} for id in ids ]
            }    
            if key : payload['_key'] = key

            self.logger.info(f""" ---- MWCal upsert dump ---- {json.dumps(payload, indent=4)} """)
            try:
                res = self.mw_kvstore.write_object(key, payload, is_partial=True)
                results.append({**payload, **res})

            except Exception as e:
                self.logger.error(f"ERROR upserting MW: {e}")
                results.append({**payload, **{"status":"failed", 
                          "message" : f"""Error: {str(e)}
If you are trying to update an existing object did you pass the kvstore _key as key=<giud> """ } } )

        return results

    def delete(self, events):
        results = []
        for e in events:
            regex = e.get("regex", self.opt_regex)
            force = e.get("force_delete", False)
            if len(regex)>2 or force:
                filter=self.mw_kvstore.get_filter(field="title", regex=regex)
                uri = self.mw_kvstore.get_uri()
                self.logger.info(f"Deleting MW Calendars with uri:{uri} + filter:{filter}")    
                try:
                    results.append(self.mw_kvstore.handle_response(self.mw_kvstore.service.delete(uri, filter=filter), "mwcal::delete_object"))
                except Exception as e:
                    self.logger.error(f"ERROR Deleteing MW: {e}")
                    results.append({"status":"failed", "message":str(e), "filter":filter})
            else:
                results.append({"status":"failed", 
                          "message" : f"""Please verify the regex provided for delete: '{regex}', use force=True as a hammer but put on your safety glasses and test your regex"""})
        return results
                

if __name__ == '__main__':
    dispatch(MWCalCommand, module_name=__name__)

