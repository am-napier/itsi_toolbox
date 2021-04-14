#!/usr/bin/env python
# coding=utf-8
#
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.client import Endpoint

import json
import time
import urllib


@Configuration()
class UpdateEpisodeCommand(StreamingCommand):
    """
    Processes parts of events that match a given regular expression.

    This command can be placed on the middle of a search pipeline:

        .. code-block:: text
        <your_search> | episodeupdate | <your_search>

    """

    # region Command options
    opt_itsi_group_id = Option(
        doc='''
        **Syntax:** **group=***<fieldname>*
        **Description:** Name of the field containing the id of the episode. Must be a valid fieldname.
        **Default:** itsi_group_id''',
        name='group',
        require=True,
        default='itsi_group_id',
        validate=validators.Fieldname())

    opt_itsi_policy_id = Option(
        doc='''
        **Syntax:** **policy=***<fieldname>*
        **Description:** Name of the field containing the id of the notable event aggreogation policy. Must be a valid fieldname.
        **Default:** itsi_policy_id''',
        name='policy',
        require=True,
        default='itsi_policy_id',
        validate=validators.Fieldname())

    opt_owner = Option(
        doc='''
        **Syntax:** **owner=***<fieldname>*
        **Description:** Name of the field containing the owner of the episode. Must be a valid fieldname.
        **Default:** owner''',
        name='owner',
        require=False,
        default=None,
        validate=validators.Fieldname())

    opt_severity = Option(
        doc='''
        **Syntax:** **severity=***<fieldname>*
        **Description:** Name of the field containing the severity of the episode. Must be a valid fieldname.
        **Default:** current severity of the episode''',
        name='severity',
        require=False,
        default=None,
        validate=validators.Fieldname())

    opt_status = Option(
        doc='''
        **Syntax:** **status=***<fieldname>*
        **Description:** Name of the field containing the status of the episode. Must be a valid fieldname.
        **Default:** current status of the episode''',
        name='status',
        require=False,
        default=None,
        validate=validators.Fieldname())

    opt_title = Option(
        doc='''
        **Syntax:** **title=***<fieldname>*
        **Description:** Name of the field containing the owner of the episode. Must be a valid fieldname.
        **Default:** title''',
        name='title',
        require=False,
        default=None,
        validate=validators.Fieldname())

    opt_description = Option(
        doc='''
        **Syntax:** **description=***<fieldname>*
        **Description:** Name of the field containing the description of the episode. Must be a valid fieldname.
        **Default:** description''',
        name='description',
        require=False,
        default=None,
        validate=validators.Fieldname())

    opt_break_episode = Option(
        doc='''
        **Syntax:** **break_episode=***<fieldname>*
        **Description:** Name of the field containing truthy value . Must be a valid fieldname.
        **Default:** break_episode''',
        name='break_episode',
        require=False,
        default=False,
        validate=validators.Fieldname())

    # endregion

    # region Command implementation
    def __init__(self):
        super(UpdateEpisodeCommand, self).__init__()
        self.logger.debug("New RUN STARTS HERE")

    def prepare(self):
        self.endpoint = Endpoint(self.service, '/servicesNS/nobody/SA-ITOA/event_management_interface/vLatest')
        return

    def stream(self, records):
        """
        Process all events. We do not expect any of the processed
        fields to be multi valued!

        :param records: An iterable stream of events from the command pipeline.
        :return: `None`.
        """
        self.logger.debug('Entering stream.{}'.format(records))
        t1 = time.time()
        # Put your event transformation code here
        for record in records:
            self.logger.info('Record {0}'.format(record))
            t2 = time.time()
            itsi_group_id = record.get(self.opt_itsi_group_id)
            itsi_policy_id = record.get(self.opt_itsi_policy_id)
            owner = record.get(self.opt_owner)
            severity = record.get(self.opt_severity)
            status = record.get(self.opt_status)
            title = record.get(self.opt_title)
            description = record.get(self.opt_description)
            break_episode = record.get(self.opt_break_episode)

            record["Updated"] = "True"

            self.logger.info(
                'episodeupdate params are : break_episode="{}" itsi_group_id="{}" itsi_policy_id="{}" status="{}" severity="{}" owner="{}" title="{}" description="{}" username="{}"'.format(
                    break_episode, itsi_group_id, itsi_policy_id, status, severity, owner, title, description,
                    self.metadata.searchinfo.username))
            """
            POST request to break episode
            """
            payload = {'_key': itsi_group_id}
            if title:
                payload['title'] = urllib.quote(title)
            if description:
                payload['description'] = urllib.quote(description)
            if status:
                payload['status'] = status
            if severity:
                payload['severity'] = severity
            if owner:
                payload['owner'] = owner

            json_payload = json.dumps(payload)
            path="notable_event_group/"+itsi_group_id
            self.logger.info('1.0 path={} data={}'.format(path, json_payload))
            r = None
            try:
                if break_episode:
                    if itsi_policy_id and title and description:
                        self.logger.info("breaking update will run update here")
                        r = self.endpoint.post(path_segment=path ,is_partial=1, break_group_policy_id=itsi_policy_id,
                                               body=json_payload)
                        record["Updated"] = "episode broken"
                    else:
                        self.logger.error("No policy ID, title or description was passed can't update this episode - {}".format(json_payload))
                        record["Updated"] = "episode NOT broken, missing properties policy_id, title and/or description"
                else:
                    self.logger.info("regular update will run here")
                    r = self.endpoint.post(path_segment=path, is_partial=1, body=json_payload)
                    record["Updated"] = "episode params updated"
                if r:
                    self.logger.info('Sent POST request to update episode itsi_group_id="{}" status={}'.format(
                                    json.loads(r['body'].read())['_key'], r['status']))
            except Exception as e:
                self.logger.error('Caught exception: {}'.format(e))
            t3 = time.time()
            self.logger.info("Update Time is:{}".format(t3 - t2))
            yield record

        self.logger.info("Full update time is:{}".format(time.time() - t1))

    # endregion


if __name__ == '__main__':
    dispatch(UpdateEpisodeCommand, module_name=__name__)