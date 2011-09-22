#!/usr/bin/env python
"""
Create text data file based on a template.

usage: python Template.py [options] data_dir template_file output_file
options are:
\t--help\t\tdisplay this help
data_dir is the root directory of the weather data
template_file is the template text source file
output_file is the name of the text file to be created
"""

from datetime import datetime, timedelta
import getopt
import logging
import os
import shlex
import sys

from conversions import *
import DataStore
from Forecast import Zambretti
import Localisation
from Logger import ApplicationLogger
from TimeZone import Local, utc
import WeatherStation

class Template(object):
    def __init__(self, params, calib_data, hourly_data, daily_data, monthly_data):
        self.logger = logging.getLogger('pywws.Template')
        self.params = params
        self.calib_data = calib_data
        self.hourly_data = hourly_data
        self.daily_data = daily_data
        self.monthly_data = monthly_data
        # set language before importing wind_dir_text array
        WeatherStation.set_translation(self.params.translation.gettext)
    def process(self, live_data, template_file):
        def jump(idx, count):
            while count > 0:
                new_idx = data_set.after(idx + timedelta(seconds=1))
                if new_idx == None:
                    break
                idx = new_idx
                count -= 1
            while count < 0:
                new_idx = data_set.before(idx)
                if new_idx == None:
                    break
                idx = new_idx
                count += 1
            return idx, count == 0
        params = self.params
        if not live_data:
            live_data = self.calib_data[self.calib_data.before(datetime.max)]
        pressure_trend_text = WeatherStation.pressure_trend_text
        wind_dir_text = WeatherStation.get_wind_dir_text()
        dew_point = WeatherStation.dew_point
        wind_chill = WeatherStation.wind_chill
        apparent_temp = WeatherStation.apparent_temp
        pressure_offset = eval(self.params.get('fixed', 'pressure offset'))
        # start off with no time rounding
        round_time = None
        # start off in hourly data mode
        data_set = self.hourly_data
        # start off in utc
        time_zone = utc
        # jump to last item
        idx, valid_data = jump(datetime.max, -1)
        if not valid_data:
            self.logger.error("No summary data - run Process.py first")
            return
        data = data_set[idx]
        # open template file file
        tmplt = open(template_file, 'r')
        # do the text processing
        while True:
            line = tmplt.readline()
            if line == '':
                break
            parts = line.split('#')
            for i in range(len(parts)):
                if i % 2 == 0:
                    # not a processing directive
                    if parts[i] != '\n':
                        yield parts[i]
                    continue
                command = shlex.split(parts[i])
                if command == []:
                    # empty command == print a single '#'
                    yield '#'
                elif command[0] in data.keys() + ['calc']:
                    # output a value
                    # format is: key fmt_string no_value_string conversion
                    # get value
                    if command[0] == 'calc':
                        x = eval(command[1])
                        del command[1]
                    else:
                        x = data[command[0]]
                    if command[0] == 'wind_dir' and data['wind_ave'] < 0.3:
                        x = None
                    # adjust time
                    if isinstance(x, datetime):
                        if round_time:
                            x += round_time
                        x = x.replace(tzinfo=utc)
                        x = x.astimezone(time_zone)
                    # convert data
                    if x != None and len(command) > 3:
                        x = eval(command[3])
                    # get format
                    fmt = '%s'
                    if len(command) > 1:
                        fmt = command[1]
                    # write output
                    if x == None:
                        if len(command) > 2:
                            yield command[2]
                    elif isinstance(x, datetime):
                        yield x.strftime(fmt)
                    else:
                        yield fmt % (x)
                elif command[0] == 'monthly':
                    data_set = self.monthly_data
                    idx, valid_data = jump(datetime.max, -1)
                    data = data_set[idx]
                elif command[0] == 'daily':
                    data_set = self.daily_data
                    idx, valid_data = jump(datetime.max, -1)
                    data = data_set[idx]
                elif command[0] == 'hourly':
                    data_set = self.hourly_data
                    idx, valid_data = jump(datetime.max, -1)
                    data = data_set[idx]
                elif command[0] == 'raw':
                    data_set = self.calib_data
                    idx, valid_data = jump(datetime.max, -1)
                    data = data_set[idx]
                elif command[0] == 'live':
                    data_set = self.calib_data
                    idx = datetime.max
                    valid_data = True
                    data = live_data
                elif command[0] == 'timezone':
                    if command[1] == 'utc':
                        time_zone = utc
                    elif command[1] == 'local':
                        time_zone = Local
                    else:
                        self.logger.error("Unknown time zone: %s", command[1])
                        return
                elif command[0] == 'roundtime':
                    if eval(command[1]):
                        round_time = timedelta(seconds=30)
                    else:
                        round_time = None
                elif command[0] == 'jump':
                    prevdata = data
                    idx, valid_data = jump(idx, int(command[1]))
                    data = data_set[idx]
                elif command[0] == 'goto':
                    prevdata = data
                    new_idx = data_set.after(DataStore.safestrptime(command[1]))
                    if new_idx:
                        idx = new_idx
                        data = data_set[idx]
                        valid_data = True
                    else:
                        valid_data = False
                elif command[0] == 'loop':
                    loop_count = int(command[1])
                    loop_start = tmplt.tell()
                elif command[0] == 'endloop':
                    loop_count -= 1
                    if valid_data and loop_count > 0:
                        tmplt.seek(loop_start, 0)
                else:
                    self.logger.error(
                        "Unknown processing directive: #%s#", parts[i])
                    return
        tmplt.close()
        return
    def make_text(self, template_file, live_data=None):
        result = ''
        for text in self.process(live_data, template_file):
            result += text
        return result
    def make_file(self, template_file, output_file, live_data=None):
        of = open(output_file, 'w')
        for text in self.process(live_data, template_file):
            of.write(text)
        of.close()
        return 0
def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "", ['help'])
    except getopt.error, msg:
        print >>sys.stderr, 'Error: %s\n' % msg
        print >>sys.stderr, __doc__.strip()
        return 1
    # check arguments
    if len(args) != 3:
        print >>sys.stderr, 'Error: 3 arguments required\n'
        print >>sys.stderr, __doc__.strip()
        return 2
    # process options
    for o, a in opts:
        if o == '--help':
            print __doc__.strip()
            return 0
    logger = ApplicationLogger(1)
    return Template(
        DataStore.params(args[0]),
        DataStore.calib_store(args[0]), DataStore.hourly_store(args[0]),
        DataStore.daily_store(args[0]), DataStore.monthly_store(args[0])
        ).make_file(args[1], args[2])
if __name__ == "__main__":
    sys.exit(main())
