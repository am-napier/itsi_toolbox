
# coding=utf-8
#

import email_server
import sys, socket

addr = ('0.0.0.0', 8025)
noddy = email_server.SplunkTestEmailServer(addr)
noddy.run()

def run():
    print("1-count, 2-pop, 3-clear, 4-quit")
    opt = sys.stdin.readline()[:1]
    if opt == '1':
        print("There are %d emails" % len(noddy.emails))
    elif opt == '2':
        print("Email: {}".format(noddy.emails.pop()))
    elif opt == '3':
        print("Email cleared.")
        noddy.clear()
    elif opt == '4':
        return
    else:
        print("Bad option ... '{}' ".format(opt))
    run()

run()
noddy.stop()
print("Email shutdown.")
