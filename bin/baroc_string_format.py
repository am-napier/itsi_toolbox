'''
Class to handle parsing of truesight baraoc epressions.
'''

import re
import logging


class BarocStringFormat:

    def __init__(self):
        self.logger = logging.Logger.manager.getLogger(self.__class__.__name__)
        self.debug_msg = ""
        self.STREXTRACT_REX = 'strextract\([^\]]+'
        self.STRREPLACE_REX = 'strreplace\([^\]]+'
        self.STRUPPER_REX = 'upper\([^\,]+'
        self.MATCH_ON_QUOTEA_REX = '[^\"]+'


    def get_event_keys(self, input_str):
        EVENT_KEY_REX_PATTERN = '\$[^\)\],]+'
        event_keys = re.findall(EVENT_KEY_REX_PATTERN, input_str)
        keys = []
        for key in event_keys:
            keys.append(key.replace('$1.', ''))
        return keys

    def get_event_key_value(self, key, event):
        try:
            return event[key].upper()
        except KeyError as err:
            self.debug_msg = "KeyError for key={} err={} in event={}".format(key, err, event)
            self.logger.error(self.debug_msg)
            print(self.debug_msg)
        return "" #TODO Shoud this return anything?

    def string_format(self, event, event_msg, event_keys):
        for key in event_keys:
            string_pos = event_msg.find("%s")
            digit_pos = event_msg.find("%d")
            event_key_value = self.get_event_key_value(key, event)
            if string_pos != -1 and digit_pos == -1:
                event_msg = event_msg.replace("%s", event_key_value, 1)
            elif string_pos != -1 and digit_pos != -1 and string_pos < digit_pos:
                event_msg = event_msg.replace("%s", event_key_value, 1)
            else:
                event_msg = event_msg.replace("%d", event_key_value, 1)

        return event_msg

    def match_and_replace_method(self, rex, template, event):
        match = re.search(rex, template)
        if match:
            arguments = match.group(0).split(',')
            if rex == self.STREXTRACT_REX:
                try:
                    event_key = self.get_event_keys(arguments[0])
                    start = int(arguments[1])
                    end = -1 #TODO Does this need to be grabed from the event?
                    event_key_value = self.get_event_key_value(event_key[0], event)
                    result = '"{}"'.format(event_key_value[start:end])
                    return template.replace(match.group(0), result)
                except IndexError as err:
                    self.debug_msg = "IndexError err={}".format(err)
                    self.logger.error(self.debug_msg)
                    print(self.debug_msg)

            if rex == self.STRREPLACE_REX:
                try:   
                    event_key = self.get_event_keys(arguments[0])
                    replace_string = arguments[1].strip().strip('"')
                    replace_with = arguments[2].strip().strip('"')
                    replace_n_times_in_sequence = int(arguments[3])
                    event_key_value = self.get_event_key_value(event_key[0], event)
                    result = '"{}"'.format(
                        event_key_value.replace(replace_string, replace_with, replace_n_times_in_sequence)).upper()
                    return template.replace(match.group(0), result)
                except IndexError as err:
                    self.debug_msg = "IndexError err={}".format(err)
                    self.logger.error(self.debug_msg)
                    print(self.debug_msg)

            if rex == self.STRUPPER_REX:
                try:
                    event_key = self.get_event_keys(arguments[0])
                    event_key_value = self.get_event_key_value(event_key[0], event)
                    result = '"{}"'.format(event_key_value)
                    return template.replace(arguments[0], result)
                except IndexError as err:
                    self.debug_msg = "IndexError err={}".format(err)
                    self.logger.error(self.debug_msg)
                    print(self.debug_msg)

        return template


    def match_methods(self, template, event):
        # Assumes there will be only one occurance of strextract and strreplace in a concat, and that it will be in the last position.
        template = self.match_and_replace_method(self.STREXTRACT_REX, template, event)
        template = self.match_and_replace_method(self.STRREPLACE_REX, template, event)
        template = self.match_and_replace_method(self.STRUPPER_REX, template, event)
        return template

    def string_template(self, template, event):
        '''
        :param template: string
        :param event: A Splunk event
        :return: A modified string version of input template.
        '''

        if isinstance(template, unicode):
            try:
                template = str(template.encode('ascii', 'replace'))
            except UnicodeError as err:
                self.logger.error("unable to cast template to str: template={} type={} err={}".format(template, type(template), err))

        if isinstance(template, str):
            if template.startswith("sprintf"):
                rex_result = re.findall(self.MATCH_ON_QUOTEA_REX, template)
                if len(rex_result) < 3:  # special case "sprintf("",[])"
                    return ""
                event_msg = rex_result[1]
                event_keys = rex_result[2]
                event_keys = self.get_event_keys(event_keys)
                if event_keys:
                    return self.string_format(event, event_msg, event_keys)
                return event_msg

            if template.startswith("concat"):
                template = self.match_methods(template, event)
                if template.count('"') == 2 and template.rfind("$") == -1:
                    return template[template.find('"')+1:template.rfind('"')]
                substrings = template.split(",")
                string_arguments = []
                for i, item in enumerate(substrings):
                    if item.count('"') == 2:
                        string_arguments.append(item[item.find('"') + 1:item.rfind('"')])
                    elif template.find("$"):
                        event_key = item.replace('$1.', '')
                        event_key = event_key.replace('])', '')
                        event_key_value = self.get_event_key_value(event_key, event)
                        string_arguments.append(event_key_value)
                return ''.join(string_arguments)

            if template.startswith("$"):
                return self.get_event_key_value(template.replace('$1.', ''), event)
            return template
        else:
            self.logger.error("type error, template is type={}".format(template, type(template)))

        return None
