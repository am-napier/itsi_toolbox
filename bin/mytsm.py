from __future__ import print_function
from builtins import str
import sys, os, datetime, time, json

pid = os.getpid()
start=time.time()
def log(msg):
    f = open(os.path.join(os.environ["SPLUNK_HOME"], "var", "log", "splunk", "mytsm.log"), "a")
    print(str(datetime.datetime.now().isoformat()), f"pid={pid}", msg, file=f)
    f.close()

def get(p, m, df=None):
    try:
        return m[p]
    except:
        log(f"no {p} in {m}")
    return df

#log("got arguments %s" % sys.argv)
p= json.loads(sys.stdin.read())
r=get("result", p, {})
cfg=get("configuration", p, {})
summary=get("summary", cfg, "no summary")
signature=get("signature", cfg, "no signature")
severity=get("severity", cfg, "no severity")

log(f"\n***************** MYTSM LOGGED EVENT IS summary:{summary}, signature:{signature}, severity:{severity}")
log(f"Raw Result: {json.dumps(p, indent=4)}")
log(f"Raw Config: {json.dumps(cfg, indent=4)}\n*************************")


