import sys
import splunk.admin as admin
import splunk.appbuilder as appbuilder

import logging


logger = logging.getLogger("splunk.itsim")

class GetTicketInfo(admin.MConfigHandler):
    handledActions = [admin.ACTION_LIST]

    def setup(self):
        logger.info("1111 get_ticket_info in setup 1")
        if self.requestedAction not in self.handledActions:
            raise admin.BadActionException(
                "This handler does not support this action (%d)." % self.requestedAction)


    def handleList(self, confInfo):
        """Called when user invokes the "list" action."""
        logger.info("2222 get_ticket_info in handleList 2")
        for template in appbuilder.getTemplates():
            confInfo[template].append('text', 'Hello world! Get Ticket Info 123 xxx')


# initialize the handler CONTEXT_NONE
admin.init(GetTicketInfo, admin.CONTEXT_APP_AND_USER)
