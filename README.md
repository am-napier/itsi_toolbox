# itsi_toolbox
Some resources that make some ITSI jobs a little bit easier

Clone or unzip in $SPLUNK_HOME/etc/apps
Add [splunklib](https://github.com/splunk/splunk-sdk-python/tree/master/splunklib) to itsi_toolbox/bin 

Logging is into $SPLUNK_HOME/var/log/splunk/itsi_toolbox.log

## Commands

### rmentity 

#### Description
Streaming command that delete entities you no longer want from the search bar.  Every row is treated as a discrete operation.   Do not call on hundreds of rows, instead look at the filter options to delete in batch. 

usage: 
```... | rmentity [by_id=\<boolean\> dry_run=\<boolean\> is_rex=\<boolean\>]```

| Argument | Description 
| -------- | -----------
| by_id | Uses field id to find the kvstore key to delete. When false you can specify filters to delete with, *default=true*. 
| is_rex | Applies only when by_id=false.  Changes the generated filter to use regex matching, *default=false*. 
| dry_run | Applies only when by_id=false.  When true no delete is run, each row generates information fields (called filter-{string,reponse,count} about what will be deleted, *default=false*.  

Runs in two modes:
##### id
Uses the property `id` as kvstore _key from each record to delete each entity.  This is slow but specific.

Example to delete the first 10 entities returned by the lookup 
```| inputlookup | head 10 | rename _key as id | rmentity```

##### filter
Uses a filter  comprised of two parts, filter_key and filter_value, that can target fields by value as exact text match or by regex.  If unsure of the properties available pull sample config via the [REST API](https://docs.splunk.com/Documentation/ITSI/latest/RESTAPI/ITSIRESTAPIreference#itoa_interface.2F.26lt.3Bobject_type.26gt.3B)
Use `dry_run=true` to preview the results
 
Example to delete all entities that have a property type that matched the string 2021-03-31  
```| makeresults | eval filter_key="last_update" filter_value="2021-03-31" | rmentity by_id=false```

Example to delete all entities that have a property type that matched the string 2021-03-31 anywhere in the type field  
```| makeresults | eval filter_key="last_update" filter_value="2021-03-31" | rmentity by_id=false is_rex=true```

Example delete all entities in groups of 100 at a time
```| inputlookup itsi_entities | fields title \
    | streamstats c \
    | eval group=floor(c/100) \
    | stats values(title) as t by group \
    | eval filter_value="^(".mvjoin(t, "|").")$", filter_key="title" \
    | fields - t \
    | rmentity is_rex=1, dry_run=0, by_id=0 \
    | fields - filter_value
```

## episodeeupdate
Stream command that can change the status or severity of an active (unbroken) episode.

## Dashboards
__TBC__
