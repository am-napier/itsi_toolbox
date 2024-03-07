
# itsi_toolbox
These are some resources that make some ITSI jobs a little bit easier.
Contains macros, custom commands and dashboards.  

Latest update is cp_utils.py, a standalone helper probgram to make content pack management a little bit easier.  Enables the following


## Installation:
1. Deploy as a splunk app in $SPLUNK_HOME/etc/apps.
2. Add splunklib to itsi_toolbox/lib, see lib/README.md
3. Optional - if deploying in production you might want to review permissions on commands like itsidelete, confitsi, mwcal and probably remove sleep completely

### Troubleshooting:
Logging is provided in $SPLUNK_HOME/var/log/splunk/itsi_toolbox.log.
If commands fail first check the search log (from job inspector), usually its no splunklib, then check the itsi_toolbox.log.

## cp_utils.py
Enables actions from the CLI to

### For custom content packs
* **list** all the installed apps
* **status** gets the status of the named app and its components
* **deploy** the features of the named app, ie add them to the kvstore so they can be used in ITSI
* **refresh** the status of all content packs in case you deleted its objects, ie runs itsicontentpackstatus command from search 
* **clean** removes the named app's components from the system, leaves the app folder in place

### For authored content
* **author_list** lists all the known authored content packs
* **author_status** gets the status of the current named app
* **author_install** installs the named app
* **author_fetch** create the file for the CP authorship definition, uses <--name>.json as default filename
* **author_remove** remove the named authorship record from the kvstore

See the help for details on arguments required for each combination of commands:
splunk cmd python cp_utils.py [-h] [--help] [help]


## Macros
### itoa_rest(type, field, regex [, fields])
Macro to hide implementation of calling rest API for itoa_interface.  Auto extracts _key as id and title from the returned JSON for you.  4th argument is optional and defaults to _key,title.  
Run it and expand it to see what it does.


#### args
|argument|description|
|-----------|---------|
|type|one of the values from get supported objects, e.g. service, entity, glass_table etc|
|field|name of the field to search for, e.g. host, title, _key|
|regex|unbounded regex to use in the search, note this means it contains the string|
|fields| CSV list of fields to return, default is title,_key|
#### usage:
```| `itoa_rest("<type>", "<field>", "<value", "<field_list>")` ```
#### examples:
List all services that start with Buttercup and return id (aka _key), title and kpis:
```| `itoa_rest("status", "title", "^Butter", "_key,title,kpis")` ```

List all services but return just id and title (note 3 arg version):
```| `itoa_rest("status", "title", "^Butter")` ```

Get all entities that have a host field (info or alias) that starts with `win`
```| `itoa_rest("entity", "host", "^win", "_key,title,_status")` ```

Get all the glasstables, all the fields...
```| `itoa_rest("glass_table", "title", "", "")` ```

Append these handy snippet gets all extra fields from the json, add the fields you want to extract

Gets any text or object attributes 
`| foreach identifier mod_source mod_timestamp [| eval <<FIELD>>=spath(value, "<<FIELD>>")]`

Gets any arrays, ie alias and info values
`| foreach host [| eval <<FIELD>>=spath(value, "<<FIELD>>{}")]`

Gets hidden system properties and displays them as sys*
`| foreach _user _key _type [| eval sys<<FIELD>>=spath(value, "<<FIELD>>")]`


**Note** there are a few wrappers using this macro you can play with but in practice I just default to itoa_rest.
 - get_svc_json(3) 
 - get_svc_json(2) 
 - get_entity_json(3) 
 - get_entity_json(2)

### service_tree_dependencies(n)
Gets the child services of the services passed.
#### args
n - is the level to extract

#### example:
List 3 levels of services under the service called Splunk
```
| `itoa_rest("service", "title", "^Splunk$", "_key,title")`
| eval level=1, value=null()
`service_tree_dependencies(1)`
`service_tree_dependencies(2)`
`service_tree_dependencies(3)` 
```

### get_payload
Concatenates all values of payload into a json array called payload.  This is used by confitsi command to format the payload used for updates.  There is a second version with an argument for the name of the field to query/build but I've never found cause to use it.

#### examples:
Construct a field called payload to generate 3 services 
```
 | makeresults count=2 | streamstats c 
 | eval payload=json_object("_key", "id-".c, "title", "Service ".c) 
 | `get_payload` 
 ```
 ##### outputs
``` 
[{"_key":"id-1","title":"Service 1"},{"_key":"id-2","title":"Service 2"}] 
```

### entity_filter(<field_name>, <field_value>, [<field_type>, [<match_type>]])
Constructs an entity filter object that can be used to make entity filters for service updates via the confitsi command.
There are 3 versions

 - entity_filter(field_name,field_value)
 - entity_filter(field_name,field_value,field_type)
 - entity_filter(field_name,field_value,field_type,match_type)

#### args
|argument|description|
|---|---|
|field_name|name of the entity match field, e.g. host, datacentre etc.|
|field_value|the value to match, e.g. win*, dc1, *|
|field_type|one of info, alias or entity_type|
|match_type|one of 'matches' or 'does not match'|

The macro just wrappers this code: 
```
`json_object("field", "$field_name$", "field_type", "info", "value", "$field_value$", "rule_type","$match_type$")`
```
#### example:
update some services with new filters
```
| `itoa_rest("service", "title", "a_test_1", "_key,title,entity_rules")`
| eval payload=json_object("_key", "----id----", 
"entity_rules", json_array(json_object(`entity_rule`, 
  json_array(
  `entity_filter("database", "ora")`, 
  `entity_filter("database", "sql")`, 
  `entity_filter("host", "sql*", "alias")`, 
  `entity_filter("host", "*123", "alias", "not")`)
  ) ) ) 
```
*Pro-tip - to see how it should look use ```| `itoa_rest` ... | prettyprint``` *

### mw_rest(title_regex)
List all the maintenance windows that match title_regex, same behaviour as itoa_rest

## Commands

### itsidelete
Command to delete services, entities or [any supported_other objects](https://docs.splunk.com/Documentation/ITSI/4.17.0/RESTAPI/ITSIRESTAPIreference#itoa_interface.2Fget_supported_object_types:~:text=in%20your%20environment.-,itoa_interface/get_supported_object_types,-Get%20a%20list) from the search bar.  
*Note: a value of pattern=abc matches any field that *contains* abc while ^abc matches starts-with abc.*

usage: 
```
| itsidelete type=<objecttype> field=<string> pattern=<unbounded_regex> confirm=<bool>
```

| Argument | Description 
| -------- | -----------
| type | one of the values from get_supported_object types, *default=None*.  
| field | the name of a field to search with, *default=title*.  
| pattern | an unbounded regex to match values in <field>, *default=None*.  
| confirm | Set to 1 to commit the action, Set to 0 (or omit) to test, *default=0*.  

Use `confirm=0` to preview the results
 
## episodeupdate

#### Description
Streaming command that can change the status or severity of an active (unbroken) episode, including breaking.  Status and severity updates are immediate however when breaking an episode the REST endpoint does not do it immediately but posts a new tracked alert (source=itsi@internal@group_closing_event) that must then be picked up by the rules engine and subsequently processed.  This can take in excess of 60 seconds.
 
usage: 
```...<your search> | episodeupdate ```

This command takes no arguments but it extracts values from each event that is passed in.  It expects a number of fields in the records passed:
| Field | Description 
| -------- | -----------
| itsi_group_id | ITSI group id 
| itsi_policy_id | policy of the generating NEAP, required only if breaking the episode 
| severity | The integer status to set, see [itsi_notable_event_severity.conf](https://docs.splunk.com/Documentation/ITSI/4.7.2/Configure/itsi_notable_event_severity.conf)  
| status | The integer status to set, see [itsi_notable_event_status.conf](https://docs.splunk.com/Documentation/ITSI/4.7.2/Configure/itsi_notable_event_status.conf)  
| break | Pass something that looks like a boolean, tests the first char for 1, t or y.  All other cases are false (incl default)   

Note that at the time of writing the API required owner, title and description to be in the payload but they are never used.  The underlying code inserts dummy values of "N/A" in those fields.
Would be lovely if one day we could also change the title and description etc of the episode this way as well ([splunk idea](https://ideas.splunk.com/?project=ITSIID) anyone?).

Example: 
```
    | inputlookup itsi_notable_group_user_lookup 
    | rename _key as itsi_group_id 
    | lookup itsi_notable_group_system_lookup _key as itsi_group_id 
    | search is_active=1 title="*"
    | rename policy_id as itsi_policy_id
    | eval break="t", severity=1, status=5
    | episodeupdate
```

## confitsi
Apart from confit being the hands down best way to cook almost anything, this command is a swiss army knife for the search bar, **but** you need to know how the REST API structures data in the kvstore.  While [this](https://docs.splunk.com/Documentation/ITSI/latest/RESTAPI/ITSIRESTAPIschema) is good, nothing beats a bit of experimenting with ``` `itoa_rest` ... | prettyprint ```  to help you discover how things work.

**Caution: backup the kvstore first and be prepared to make mistakes so have a rollback plan ready.**

This command does little more than call the relevant end point.  It does no checking of the data, the API (or your SPL) does that.  
### Examples
There are too many great recipes when learning to cooking food in various melted fats so here are just a couple.  I didn't say this would always be healthy but it is so very tasty.  


#### Create an entity 

```
| makeresults 
| eval payload=printf("[%s]", json_object("_key", "my-entity", "title", "My Entity"))
| confitsi type=service confirm=1
```

#### Create some services with KPIs

What are the minimum set of properties you need to create a KPI on a service?  
This really is just a contrived example, use templates instead if you need to make KPIs.
```
| makeresults | eval id=split("A1,B1,B2,B3", ","), srch="| makeresults | eval x=random()%10+21" 
| mvexpand id
| eval payload=json_object("_key", id, "title", id, "kpis", 
            json_array(json_object("_key", id."_boom_kpi", 
                                   "title", "boom_kpi", 
                                   "search", srch, 
                                   "base_search", srch, 
                                   "threshold_field", "x", 
                                   "aggregate_statop", "avg", 
                                   "urgency", 6, 
                                   "alert_period", 5, 
                                   "search_alert_earliest", 5)))
`get_payload`
| confitsi type=service confirm=1
```

### Update a KPI urgency
With this example we need to preserve the contents of the array of KPIs and just update the fields we want to touch.  The REST API doesn't do is_partial on sub-objects in its schema.  That means if you build a sub-object like a KPI and don't include existing properties then they will be removed when you update the object, therefore you **must** read the object update the bits you want to change, while keeping the rest, and then write it back.

```
| `itoa_rest("service", "title", "a_test_1", "_key,title,kpis")`
| eval value=spath(value, "kpis{}")
| mvexpand kpi
| eval kpi_title=spath(kpi, "title")
| search kpi_title="k1"
| eval payload=printf("[%s]", 
    json_object("_key", id, 
                "base_service_template_id", "", 
                "kpis", json_array(
                    json_set(kpi, 
                       "urgency", 3, 
                       "unit", "secs", 
                       "description", "my messaed up KPI", 
                       "base_service_template_id", "")
                 )
               )
           )
     , kpi=null()
| confitsi type=service confirm=1
```

### Change Entity Filter


```
| makeresults 
| eval serviceid="INSERT YOUR GUID HERE", payload=json_object(
    "_key", serviceid, 
    "title", service_name, ``` not needed if the service exists ```
    "entity_rules", json_array(json_object(`entity_rule`, 
  json_array(
  `entity_filter("database", "ora")`, 
  `entity_filter("database", "sql")`, 
  `entity_filter("host", "sql*", "alias")`, 
  `entity_filter("host", "*123", "alias", "not")`)
  ) ) )
`get_payload`
| confitsi type=service confirm=1 
```
Notes:
- macro get_payload creates the payload property from all rows into one so confitsi can run one update in bulk mode. While confitsi will run in single update mode that is very ineffiecent so get_payload does a stats values(payload) and then writes the output to an array (see Shift-Cmd E)

- confirm set to 0 will just write the prettyprint JSON to the search bar, no updates will be done. Good to validate what it is going to do.
- When it works you get the ids of the new objects written to confitsi.response
- When it fails you’ll get errors written in confitsi.error

*Pro-tip* Don't forget to check the debug log itsi_toolbox.log

### mwcal
Create, update and delete maintenance windows from the search bar.
Note all properties are required for an update even if they are not being updated
This is a streaming command and gets its input from the events for each row, therefore it can 
operate on many objects in a single search, but it will be slow.

Create and update are essentially the same except you pass the key for an update, no key to create.
Events require the following:
|argument|description|
|--------|-----------|
|start | an epoch time|
|end | an epoch time, note you can pass duration (in mins) instead and it will be combined with start |
|title | the string name of the calendar |
|ids | a multi-value list of ids for the objects being added |
|type | one of entity or service depending on your ids. |

Delete has two forms, see examples

#### Examples
Create some windows from a lookup, assume the lookup has a row for each entity with start time and duration ...
``` 
| inputlookup mw.csv
| stats values(entity_key) as ids by start, duration
| eval title=printf("Entity maintenance %s to %s", strftime(start, "%F %T"), strftime(start+duration*60, "%F %T")) 
| mwcal mode=upsert
```

Update all Sunday calendars to be one week later
```
| `mw_rest("Sunday")`
| eval start=tonumber(spath(value, "start_time"))+86400*7, end=tonumber(spath(value, "end_time"))+86400*7, obj=spath(value, "objects{}") 
| mvexpand obj
| eval ids=spath(obj, "_key"), type=spath(obj, "object_type"), key=id
| stats values(ids) as ids, first(start) as start, first(end) as end by key, title, type 
| mwcal mode=upsert
```

Delete all calendars that are older than 2 weeks
```
| `mw_rest("")`
| eval end=tonumber(spath(value, "end_time")) 
| where end < now()-86400*14
| stats values(title) as regex 
| eval regex=printf("^%s$", mvjoin(regex, "|")) 
| mwcal mode=delete
```

Delete all caledars with the word easter in them
```
| makeresults | mwcal mode=delete regex=easter
```

**Note:** as always delete is permanent, perhaps consider archiving to an index before deleting


### prettyprint
Pretty prints a JSON payload 

#### usage
```
| `itoa_rest(...)` 
| prettyprint 
    [indent=<int def>] 
    [remove=<csv_string>] 
    [fields=<csv_string>]
```

|arg|description|
|---|-----------|
|indent|indents the text, defaults to 4|
|remove|comma separated list of fields to remove from the output, defaults to "object_type,sec_grp,permissions"|
|fields|comma separated list of fields to prettyprint|


### sleep 
Make the search pipeline sleep for some seconds, optionally consume CPU

#### usage
```| ... | sleep pause=<int> load=<int>```

|arg|description|
|---|-----------|
|pause|milliseconds to sleep, default=1000|
|load|percentage load to add to the system, default=0 ie no extra load|

## Dashboards:
### KPI Search Performance
Review KPI search times.  This is a pimped up version of the itsi health report with tokens that allow drilldown and expansion of KPI performance plus details on services used by those searches.

### Saved Search Performance
Provides a review saved search times, aimed at correlation searches but essentially its just a view on saved searches. Works much like KPI Search Performance.

### ITSI Import Objects
Review the import objects jobs that are running with drill-downs into the logs for errors

### Adaptive Metrics Analyzer
Its an old dashboard, there are probably better tools in the CP for monitoring and alerting but this quick dashboard allows browsing of service/kpi/entity values from itsi_summary_metrics.  Time range is Sun-Sun so we can see the patterns that might apply to timebased thresholds.  Use it to quickly explore kpi values and open the searches to see how they are  indexed.

