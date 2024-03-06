#!/usr/bin/python


import getpass, argparse
import requests, sys, json, os
from requests.auth import HTTPBasicAuth
requests.packages.urllib3.disable_warnings()

MAIN_SEP='='*120
SEP='-'*45
EXIT_HTTP_ERR = 1
EXIT_HELP_DISPLAYED = 2
EXIT_NO_APP = 3
EXIT_FILE_EXISTS = 4

PROG_NAME = "cp_utils"

def usage_help():
    print(f""" {PROG_NAME} : [--user] [--pswd] [--host] [--port] [--file] [--name] action [sub_action]
          
  This program is a helper to enable CLI and automation easier access to management functions with the REST API
  provided around ITSI content packs.
                  
  options:
          token : (string) splunk authentication token, takes precendence over user/pswd
          user  : (string) splunk user to execute with (default=admin) 
          pswd  : (string) password for the user 
          host  : (string) splunk searchhead (default=localhost)
          port  : (int) management port (default=8089)
          file  : (string) a file path for the content packs authorship definition, required for author_install and author_fetch only
          name  : (string) name of the app to work on, see app.conf.ui.label or itsi/config.json->title**
          cert  : (string) path to a certificate or None to ignore (default None)
          version : (string)++ if a specific version should be used specify here (TODO)
          enabled : (unary)+ when doing action install you must explicitly enable objects being installed (default False)
          overwrite : (unary)+ when creating an authorship definition this allows overwrite of existing file (default:False) 

      + unary means its a unary option and no value should be provided for this option 
                  ie {PROG_NAME} --enabled --user bruce --pswd d0nt#m4k3@m3!m4d
      ++ versions not yet implemented, needs attention/research to understand the implications.

  action  - the task we are going to perform, one of the following
    * list    : list the installed apps (todo exclude the OOB apps)
    * status  : (requires name) get the status on the named app and its components 
    * deploy  : (requires name, optional enabled) deploy the features of the named app, ie add them to the kvstore so they can be used
    * refresh : refresh the status of all content packs, ie run after clean
    * clean   : (requires name) remove the named app's components from the system, leaves the app in place
    * author_list    : list all the known authored content packs
    * author_status  : (requires name) of the current named app
    * author_install : (requires file) install the named app, requires --file
    * author_fetch   : (requires name, optional file, overwrite) create the file for the CP authorship definition, uses name.json as default filename
    * author_remove  : remove the named authorship record from the kvstore
""")          
    sys.exit(EXIT_HELP_DISPLAYED)

def setup(argv):
    # [i for i in L1 if i in L2]
    if [opt for opt in ["?", "help", "-h", "--help"] if opt in argv]:
        usage_help()

    p = argparse.ArgumentParser(prog="cpauthor",
                                 description="Utility to help with tasks for content pack authorship",
                                 epilog="---When in doubt read the code---")

    # TODO: something not right here with the first arg being passed and the way ArgParser renders the usage/help
    p.add_argument(dest="action", choices="help,list,status,refresh,clean,deploy,author_list,author_status,author_install,author_fetch,author_remove".split(","), default="list",
                   help=" see --help for details ")

    p.add_argument("--user",      help="user with access to run rest calls against ITOA", type=str, default='admin')
    p.add_argument("--token",     help="valid splunk auth token, user/pswd not required", type=str)

    p.add_argument("--pswd",      help="password for named user, no default, should prompt the user if not provided", type=str)
    p.add_argument("--host",      help="Splunk server", type=str, default='localhost')
    p.add_argument("--port",      help="port for REST management interface", type=int, default=8089)
    p.add_argument("--cert",      help="path for certificate, if required", type=str, default=None)
    p.add_argument("--version",   help="content pack version string", type=str, default=None)
    p.add_argument("--overwrite", help="overwrite the file when running author_fetch", action="store_true", default=False)
    p.add_argument("--enabled", help="Install objects as enabled", action="store_true", default=False)
    p.add_argument("--file",   help="Path to content pack authorship json", type=str)
    p.add_argument("--name",   help="Content pack name, ie whats shown in the UI, app.conf->ui->label or itsi/config.json->title", type=str)

    '''
    def remove_options(parser, options):
    for option in options:
        for action in parser._actions:
            if vars(action)['option_strings'][0] == option:
                parser._handle_conflict_resolve(None,[(option,action)])
                break
    '''            
    def update_argument(parser, arg, kwargs):
        # loop over all actions and update the values in StoreAction with whatever is in kwargs
        for action in parser._actions:
            if vars(action)['dest'] == arg:
                for k, v in kwargs.items():
                    action.__setattr__(k, v)

    # name and file options are only required for some action types
    args = p.parse_args(argv[1:])
    if args.action in ["author_install"]:
        update_argument(p, "file", {"required": True})
    if args.action in ["status", "deploy", "clean", "author_status", "author_fetch", "author_remove"]:
        update_argument(p, "name", {"required": True})

    args = p.parse_args(argv[1:])

    session = requests.Session()
    if args.token is not None:
        session.headers.update({"Authorization" : f"Splunk: {args.token}"})        
    else:
        if args.pswd is None:
            args.pswd = getpass.getpass(f"Enter {args.user}'s password:")
        session.auth = (args.user, args.pswd)

    session.headers.update({"Content-Type":"application/json"})
    session.verify = False if args.cert is None else args.cert
    return (args, session)



class ContentPackHelper():
    def __init__(self, args, session):
        self.sess = session
        self.action = args.action.lower()
        self.url_base_itoa = f"https://{args.host}:{args.port}/servicesNS/nobody/SA-ITOA/itoa_interface"
        self.url_base_em = f"https://{args.host}:{args.port}/servicesNS/nobody/SA-ITOA/event_management_interface"
        self.args = args
        self.name = args.name
        
    def _load_apps(self):    
        res = self.sess.get(f"{self.url_base_itoa}/content_pack")
        if res.status_code!=200:
            print(f"Failed to read content packs, http code:{res.status_code}, text: {res.text}")
            sys.exit(EXIT_HTTP_ERR)
        self.app_map = {}
        for cp in res.json()['items']['success']:
            self.app_map[cp['title']] =cp #{'id':cp['id'], 'version':cp['version']}


    def _load_authored_apps(self):    
        res = self.sess.get(f"{self.url_base_itoa}/content_pack_authorship/content_pack")
        if res.status_code!=200:
            print(f"Failed to read authored content packs, http code:{res.status_code}, text: {res.text}")
            sys.exit(EXIT_HTTP_ERR)
        self.authored_app_map = {}
        for cp in res.json():
            self.authored_app_map[cp['title']] =cp #{'id':cp['id'], 'version':cp['version']}



    def get_app_info(self):
        
        if self.name not in self.app_map.keys():
            print(f"\n{MAIN_SEP}\n  ERROR: The content pack called '{self.name}' is not installed.\n\n")
            sys.exit(EXIT_NO_APP)
        app = self.app_map[self.name]
        return (app['id'], app['version'])

    def list(self):
        self._load_apps()
        for name, app in self.app_map.items():
            print(f"""
{SEP}
  title  : {name}
{SEP}
version : {app['version']}
id : {app['id']}
""")

    def deploy(self):
        ''' 
        Read the preview endpoint, mangle the config and post to install
        itoa_interface/content_pack/<name>/<version>/preview
        itoa_interface/content_pack/<name>/<version>/install
        '''
        self._load_apps()
        id, version = self.get_app_info()        
        url = f"{self.url_base_itoa}/content_pack/{id}/{version}/preview"
        print(f"{MAIN_SEP}\nDeploy is reading \n{url}\n{MAIN_SEP}\n")
        res = self.sess.get(url)
        
        if res.status_code == 200:
            body = res.json()
            output = {}
            #print(f"{MAIN_SEP}\nInstalling using preview\n{MAIN_SEP}\n{json.dumps(body, indent=2)}")
            for key,value in body.items():
                if key in ['entity_types', 'glass_tables', 'glass_table_images', 
                        'services', 'kpi_base_searches', 'service_analyzers',
                        'service_templates', 'correlation_searches', 
                        'deep_dives', 'notable_event_aggregation_policies']:
                    output[key] = [i['id'] for i in value]
            output = {
                "resolution": "overwrite",
                "enabled": 1 if self.args.enabled else 0,
                "backfill": "false",
                "saved_search_action": "enable" if self.args.enabled else "disable",
                #"install_all":1
                "content" : output
            }
            '''
            now push this to the install endpoint
            '''
            #print(f" Install payload is {json.dumps(output, indent=4)}")
            res = self.sess.post(url.replace("/preview", "/install"), json=output)#, verify=self.verify)
            if res.status_code <= 299:
                print(f"{MAIN_SEP}\nInstall Response\n{MAIN_SEP}\n{json.dumps(res.json(), indent=4)}")
            else:
                print(f"Error installing CP code: {res.status_code} Text: {res.text}")

    def author_install(self):
        ''' 
        --action=author
        Read the authorship endpoint mange and post back using the different format :'/
        itoa_interface/content_pack_authorship/content_pack/<key>
        '''
        file_json=json.load(open(self.args.file))
        itsi_objects = {}
        
        for k, v in file_json['itsi_objects'].items():
            itsi_objects[k]=[]
            for obj in v:
                itsi_objects[k].append([id for id in obj.keys()][0])

        file_json['itsi_objects'] = itsi_objects

        url = f"{self.url_base_itoa}/content_pack_authorship/content_pack"
        print(f"{MAIN_SEP}\nAuthorship setup \n{url}\n{MAIN_SEP}\n")

        res = self.sess.post(url, json=file_json)
        if res.status_code == 200:
            print(f"ok: {json.dumps(res.json(), indent=8)}")
        else:
            print(f"Failed code: {res.status_code}, text: {res.text}")


    def author_list(self):
        '''
        List all the known apps
        '''
        self._load_authored_apps()
        for name, app in self.authored_app_map.items():
            app['icon'] = app['icon'][0:40]+" *** redacted ***"
            extra = ["ITSI Objects"]
            for k, v in app['itsi_objects_counts'].items():
                extra.append(f"  {v}  {k}")
            extra.append(["Splunk Objects"])
            for k, v in app['splunk_objects_counts'].items():
                extra.append(f"  {v}  {k}")
            epilogue=""    
            for i in extra:
                epilogue = f"{epilogue}\n{i}"
            print(f"""{SEP}
  title: {name}
{SEP}
description : {app["description"]}
version     : {app["cp_version"]}
status      : {app["status"]}
_key        : {app["_key"]}
{epilogue}
""")


    def author_status(self):
        '''
        Retrieve its record
        remove the reference to icon and dump to screen
        '''
        url = f'{self.url_base_itoa}/content_pack_authorship/content_pack/?filter={{"title":"{self.name}"}}'
        print(url)
        res = self.sess.get(url)

        if res.status_code == 200:
            cp = res.json()[0]
            cp['icon'] = cp['icon'][0:40]+"  ***redacted***"
            print(f"""
{MAIN_SEP}
| title: {self.name} | status: {cp['status']} | version: {cp['cp_version']} | _key: {cp['_key']}
{MAIN_SEP}
{json.dumps(cp, indent=4)}""")
        else:
            print(f"Failed code: {res.status_code}, text: {res.text}")

    def author_remove(self):
        '''
        We have the name, get the ID then delete the object
        '''
        self._load_authored_apps()
        id = self.authored_app_map[self.name]['_key']
        res = self.sess.delete(f"{self.url_base_itoa}/content_pack_authorship/content_pack/{id}")
        if res.status_code == 204:
            print(f'{MAIN_SEP}\nRemoved the content pack {self.name}\n{MAIN_SEP}') 
        else:
            print(f"{MAIN_SEP}\n  *** ERROR ***: Failed code: {res.status_code}, text: {res.text}")
            sys.exit(EXIT_HTTP_ERR)        


    def author_fetch(self):
        
        fname = self.args.name+".json" if self.args.file is None else self.args.file
        print("Fetching ; {fname}")
        self._load_authored_apps()
        id = self.authored_app_map[self.name]['_key']
        if os.path.isfile(fname) and not self.args.overwrite:
            print(f"""
  *** Error Writing file, {fname} exists and overwrite is not set.
                  """)
            sys.exit(EXIT_FILE_EXISTS)

        res = self.sess.get(f"{self.url_base_itoa}/content_pack_authorship/content_pack/{id}")
        if res.status_code == 200:
            with open(fname, "w") as fp:
                fp.write(json.dumps(res.json(), indent=4))
            print(f'File created {fname}') 
        else:
            print(f"Failed code: {res.status_code}, text: {res.text}")
            sys.exit(EXIT_HTTP_ERR)

    def rm_objects(self, type, items):
        type_map = {
            'entity_types' : 'entity_type',
            'glass_tables' : 'glass_table',
            'glass_table_images' : None,
            'services' : 'service',
            'kpi_base_searches' : 'kpi_base_search',
            'service_analyzers' : 'home_view',
            'service_templates' : 'base_service_template',
            'correlation_searches' : 'correlation_search',
            'deep_dives' : 'deep_dive',
            'notable_event_aggregation_policies' : 'notable_event_aggregation_policy'}
        print(f"Removing object types for :{type}")
        for obj in items:            
            id = obj["id"]
            ttl = obj["title"]            
            if not obj['installed']:
                print(f"    Skipped {ttl}, _key={id}, its not installed")
                continue

            if type in ['correlation_searches', 'notable_event_aggregation_policies']:
                url=f"{self.url_base_em}/{type_map[type]}/{id}"
            else:
                url=f"{self.url_base_itoa}/{type_map[type]}/{id}"
            res = self.sess.delete(url)
            if res.status_code ==204:
                print(f"    Removed {ttl}, _key={id}")
            else:
                print(f"Failed on {ttl}, _key={id}, code: {res.status_code}, message {res.text}")    
                

    def clean(self):
        ''' 
        Its a bit painful as dependent items must be deleted first
        '''
        self._load_apps()
        id, version = self.get_app_info()
        url = f"{self.url_base_itoa}/content_pack/{id}/{version}/preview"
        print(f"{MAIN_SEP}\nDeleting config for {self.name}, no backups ... \n{url}\n{MAIN_SEP}\n")
        res = self.sess.get(url)
        
        if res.status_code == 200:
            body = res.json()            

            # not cleaning these or we need to do it differently 
            keys = [i for i in body.keys() if i not in ["saved_searches"] ]

            # delete the things that need to go first, ie services before templates before kpi_base_searches
            for item in ['deep_dives', 'glass_tables', 'glass_table_images', 'service_analyzers', 
                                    'correlation_searches', 'services','entity_types', 'service_templates', 
                                    'kpi_base_searches', 'notable_event_aggregation_policies']:
                if item in body :
                    self.rm_objects(item, body[item])
                    keys.remove(item)
            # then delete the rest    
            for item in keys:
                self.rm_objects(item, body[item])
                


    def status(self):
        '''
        Gets te status of items i the named CP
        '''
        self._load_apps()
        id, version = self.get_app_info()

        url = f"{self.url_base_itoa}/content_pack/{id}/{version}/preview"
        print(f"{MAIN_SEP}\nStatus for\n{url}\n{MAIN_SEP}\n")
        res = self.sess.get(url)#, verify=self.verify)
        if res.status_code == 200:
            all_configs = res.json()
            for object_type in all_configs:
                if type(all_configs[object_type]) == list:
                    table_header = f"| enabled |{' title':<60}|_key\n{'-'*10}|{'-'*60}|{'-'*20}"
                    print(f"\n{object_type.upper()}\n{MAIN_SEP}\n{table_header}")
                    for i in all_configs[object_type]:                    
                        print(f'| {"True" if i["installed"] else "False":<8}| {i["title"]:<59}| {i["id"]:<40}')
                else:
                    print(f"\n{object_type.upper()}\n{MAIN_SEP}\n{json.dumps(all_configs[object_type])}\n")                    
        else:
            print(f"Failed {res}")

    def refresh(self):
        ''' 
        Need to run the following ssearch -->> | itsicontentpackstatus
        The current impl doesn't do jack
        '''
        url = f"{self.url_base_itoa}/content_pack/refresh"
        res = self.sess.post(url)#, verify=self.verify)
        if res.status_code == 200:
            print(f"Refreshed OK {json.dumps(res.json(), indent=4)}")
        else:
            print(f"Failed {res}")


    def run(self):
        '''
        do the thing this user asked for
        '''
        fn = getattr(self, self.action)
        if fn is not None:
            fn()
        else:
            print(f"Unknown Action: {self.action},\n   ARGS:{json.dumps(vars(self.args), indent=4)}")

if __name__ == '__main__':
    helper = ContentPackHelper(*setup(sys.argv)).run()


