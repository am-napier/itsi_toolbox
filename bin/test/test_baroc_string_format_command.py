from unittest import TestCase
from bin.command_baroc_string_format import BarocStringFormatCommand
import random, string


class TestStringFormatCommand(TestCase):

    #def record = [test: "test"]

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
            'DNS answer to query slow or not responding! Parameter value = %s(1 = Slow, 2 = Not responding)' % event['mc_parameter_value'],
            'LOGStatus triggered for instance ''%s'', current status is %s' % (event['mc_object'].upper(), event['mc_parameter_value']),
            '',
            'Total Disk utilization of %s is more than %s percent' % (event['mc_object'].upper(),event['pes_alarm_min'].upper()),
            'LOGStatus triggered for instance ''%s'', current status is: ''Inactivity Error' % event['mc_object'].upper(),
            'Astro Camel client starts queueing messages! Obviously it can''t deliver through XXX! Metric: ''%s'' (%s)' % (
            event['mc_parameter'].upper(), event['mc_parameter_value'].upper()),
            'Write cache hit ratio less than %s %%%%' % event['pes_alarm_max'].upper(),
            'The number of open sessions is close to the maximum number of licensed sessions',
            'An order event has been sent to XXX with and application exceptions for a long time. Probably because XXX has been in night batch mode to long.',
            event['msg'].upper(),
            'BS::APS::XXX',
            'APP::' + event["Alias_Obj"].upper(),
            'SS::IBM_WAS::' + event['Alias_Obj'].upper() + "::" + event['Alias_ObjOwner'].upper(),
            'SS::IIP::' + event["Alias_Param"][1:-1].upper(),
            'RP::' + event["mc_host"].upper() + "::" + event["Alias_Obj"].upper(),
            'APP::' + event["Alias_Obj"].replace("_", "", 1).upper(),
            'Message %s detected in alert log on device.' % event['mc_object'].upper(),
            'A system error has occured when sending order event to XXX. Probably because XXX WS is down, but it could also be other errors.'

        ]

    def test_stream(self):
        key_value = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10)) + '_'
        base_event = self.get_event(key_value)
        expected = self.get_expected(base_event)

        templates = [
            'sprintf("DNS answer to query slow or not responding! Parameter value = %s(1 = Slow, 2 = Not responding)", [$1.mc_parameter_value])',
            'sprintf("LOGStatus triggered for instance ''%s'', current status is %d", [$1.mc_object, stringtoint($1.mc_parameter_value)])',
            'sprintf("",[])',
            'sprintf("Total Disk utilization of %s is more than %s percent", [$1.mc_object,$1.pes_alarm_min])',
            'sprintf("LOGStatus triggered for instance ''%s'', current status is: ''Inactivity Error''", $1.mc_object)',
            'sprintf("XXX client starts queueing messages! Obviously it can''t deliver through IIP! Metric: ''%s'' (%s)", $1.mc_parameter, $1.mc_parameter_value)',
            'sprintf("Write cache hit ratio less than %s %%", $1.pes_alarm_max)',
            'sprintf("The number of open sessions is close to the maximum number of licensed sessions",)',
            'concat(["An order event has been sent to COS with and application exceptions for a long time. Probably because COS has been in night batch mode to long."])',
            '$1.msg',
            'BS::APS::XXX',
            'concat(["APP::",$1.Alias_Obj])',
            'concat(["SS::IBM_WAS::",$1.Alias_Obj, "::",$1.Alias_ObjOwner])',
            'concat(["SS::IIP::",strextract($1.Alias_Param,1,len($1.Alias_Param)-1)])',
            'concat(["RP::",upper($1.mc_host),"::",$1.Alias_Obj])',
            'concat(["APP::", strreplace($1.Alias_Obj, "_", "", 1, 1)])',
            'sprintf("Message ''%s'' detected in alert log on device.", [$1.mc_object])',
            'concat(["A system error has occured when sending order event to Centiro. Probably because XXX WS is down, but it could also be other errors."])'
        ]

        gen_stream = BarocStringFormatCommand()
        records = []

        for temp in templates:
            base_event['template'] = temp
            records.append(base_event.copy())

        my_gen = gen_stream.stream(records)
        run_test_starting_with_index = 0
        # record_list = [records[run_test_starting_with_index]]
        #my_gen = gen_stream.stream2(record_list)

        print("Starting test run")
        print("Key Value: %s \n" % key_value)
        count = run_test_starting_with_index
        for i in my_gen:
            print("Input_    %s" % templates[count])
            print("Expected: %s" % expected[count])
            print("Actual:   %s \n" % i['ops_msg'])
            self.assertEqual(expected[count], i['ops_msg'])
            count += 1

    def test_normalize_debug(self):
        obj = BarocStringFormatCommand()

        true_inputs = [
            'true',
            'True',
            't',
            '1',
            'Yes',
            'y']

        false_inputs = [
            'False',
            'false',
            'f',
            '0',
            '-1',
            'No',
            'n'
        ]
        for item in true_inputs:
            self.assertTrue(obj.normalize_debug(item))

        for item in false_inputs:
            self.assertFalse(obj.normalize_debug(item))




