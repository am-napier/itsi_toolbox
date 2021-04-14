from unittest import TestCase
import unittest, random, string
from bin.baroc_string_format import BarocStringFormat

class TestMatchTable(TestCase):

    def get_event(self, key_value):
        event = {
            "mc_host": key_value,
            "param": "param - 1",
            "status": 321,
            "bool": True,
            "mc_object": key_value,
            "mc_parameter": key_value,
            "mc_parameter_value": "123",
            "mc_object": key_value,
            "pes_alarm_min": key_value,
            "pes_alarm_max": key_value,
            "msg": key_value,
            "Alias_Param": key_value,
            "Alias_Obj": key_value,
            "Alias_ObjOwner": key_value,
            "msg": key_value
        }
        return event

    def get_expected(self, event):
        return [
            'DNS answer to query slow or not responding! Parameter value = %s(1 = Slow, 2 = Not responding)' % event[
                'mc_parameter_value'],
            'LOGStatus triggered for instance ''%s'', current status is %s' % (
            event['mc_object'].upper(), event['mc_parameter_value']),
            '',
            'Total Disk utilization of %s is more than %s percent' % (
            event['mc_object'].upper(), event['pes_alarm_min'].upper()),
            'LOGStatus triggered for instance ''%s'', current status is: ''Inactivity Error' % event[
                'mc_object'].upper(),
            'XXX client starts queueing messages! Obviously it can''t deliver through IIP! Metric: ''%s'' (%s)' % (
                event['mc_parameter'].upper(), event['mc_parameter_value'].upper()),
            'Write cache hit ratio less than %s %%%%' % event['pes_alarm_max'].upper(),
            'The number of open sessions is close to the maximum number of licensed sessions',
            'An order event has been sent to XXX with and application exceptions for a long time. Probably because XXX has been in night batch mode to long.',
            event['msg'].upper(),
            'BS::APS::GEMINI',
            'APP::' + event["Alias_Obj"].upper(),
            'SS::IBM_WAS::' + event['Alias_Obj'].upper() + "::" + event['Alias_ObjOwner'].upper(),
            'SS::IIP::' + event["Alias_Param"][1:-1].upper(),
            'RP::' + event["mc_host"].upper() + "::" + event["Alias_Obj"].upper(),
            'APP::' + event["Alias_Obj"].replace("_", "", 1).upper(),
            'Message %s detected in alert log on device.' % event['mc_object'].upper(),
            'A system error has occured when sending order event to XXX. Probably because XXX WS is down, but it could also be other errors.'

        ]


    def test_string_template(self):
        inputs = [
            'sprintf("DNS answer to query slow or not responding! Parameter value = %s(1 = Slow, 2 = Not responding)", [$1.mc_parameter_value])',
            'sprintf("LOGStatus triggered for instance ''%s'', current status is %d", [$1.mc_object, stringtoint($1.mc_parameter_value)])',
            'sprintf("",[])',
            'sprintf("Total Disk utilization of %s is more than %s percent", [$1.mc_object,$1.pes_alarm_min])',
            'sprintf("LOGStatus triggered for instance ''%s'', current status is: ''Inactivity Error''", $1.mc_object)',
            'sprintf("Astro Camel client starts queueing messages! Obviously it can''t deliver through IIP! Metric: ''%s'' (%s)", $1.mc_parameter, $1.mc_parameter_value)',
            'sprintf("Write cache hit ratio less than %s %%", $1.pes_alarm_max)',
            'sprintf("The number of open sessions is close to the maximum number of licensed sessions",)',
            'concat(["An order event has been sent to XXX with and application exceptions for a long time. Probably because COS has been in night batch mode to long."])',
            '$1.msg',
            'BS::APS::GEMINI',
            'concat(["APP::",$1.Alias_Obj])',
            'concat(["SS::IBM_WAS::",$1.Alias_Obj, "::",$1.Alias_ObjOwner])',
            'concat(["SS::IIP::",strextract($1.Alias_Param,1,len($1.Alias_Param)-1)])',
            'concat(["RP::",upper($1.mc_host),"::",$1.Alias_Obj])',
            'concat(["APP::", strreplace($1.Alias_Obj, "_", "", 1, 1)])',
            'sprintf("Message ''%s'' detected in alert log on device.", [$1.mc_object])',
            'concat(["A system error has occured when sending order event to XXX. Probably because XXX WS is down, but it could also be other errors."])'
        ]

        ## Run test
        key_value = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10)) + '_'
        obj = BarocStringFormat()
        event = self.get_event(key_value)
        expected = self.get_expected(event)

        for i in range(0, len(inputs)):
            returnMsg = obj.string_template(inputs[i], event)
            print('\n## Starting test: %i ##\n'
                  'Input:    %s \n'
                  'Expected: %s \n'
                  'Actual:   %s' % (i, inputs[i], expected[i], returnMsg))
            self.assertEqual(expected[i], returnMsg)


        ## Run test for empty event
        key_value = ''
        event = self.get_event(key_value)
        expected = self.get_expected(event)

        for i in range(0, len(inputs)):
            returnMsg = obj.string_template(inputs[i], event)
            print('\n## Starting test: %i ##\n'
                  'Input:    %s \n'
                  'Expected: %s \n'
                  'Actual:   %s' % (i, inputs[i], expected[i], returnMsg))
            self.assertEqual(expected[i], returnMsg)


        ## Run test that throw exceptions
        key_value = ''
        event = {
            "mc_host": key_value,
            "param": "param - 1",
            "status": 321,
            "bool": True
        }

        for i in range(0, len(inputs)):
            print('\n## Starting test: %i ##' % i)
            print('Input:    %s ' % inputs[i])
            print('Expected: %s ' % expected[i])
            returnMsg = obj.string_template(inputs[i], event)
            print('Actual:   %s' % (returnMsg))
            self.assertEqual(1, 1)

    if __name__ == '__main__':
        unittest.main()