#!/usr/bin/env python

"""Post weather update to WeatherUnderground
::

%s

.. Warning::
    This module has been superseded by the :doc:`pywws.toservice`
    module. It will be deleted from pywws in the next release.

Introduction
------------

`Weather Underground <http://www.wunderground.com/>`_ is a USA based
web site that gathers weather data from stations around the world.
This module enables pywws to upload readings to Weather Underground.

Configuration
-------------

If you haven't already done so, visit the Weather Underground web site
and create a member account for yourself. Then go to the `'Personal
Weather Stations' page
<http://www.wunderground.com/wxstation/signup.html>`_ and follow the
'new weather station' link. Fill in all the required details, then
click on 'submit'.

Copy your 'station ID' and password to a new ``[underground]`` section
in your ``weather.ini`` configuration file::

    [underground]
    password = secret
    station = ABCDEFG1A

Remember to stop all pywws software before editing ``weather.ini``.

Test your configuration by running ``ToUnderground.py`` (replace
``data_dir`` with your weather data directory)::

    python pywws/ToUnderground.py -vvv data_dir

This should show you the data string that is uploaded and then a
'success' message.

Upload old data
---------------

Now you can upload your last 7 days' data. Edit your ``weather.ini``
file and remove the ``last update`` line from the ``[underground]``
section, then run ``ToUnderground.py`` with the catchup option::

    python pywws/ToUnderground.py -c -v data_dir

This may take 20 minutes or more, depending on how much data you have.

Add Weather Underground upload to regular tasks
-----------------------------------------------

Edit your ``weather.ini`` again, and add ``underground = True`` to the
``[live]``, ``[logged]``, ``[hourly]``, ``[12 hourly]`` or ``[daily]``
section, depending on how often you want to send data. For example::

    [live]
    underground = True
    twitter = []
    plot = []
    text = []

If you set ``underground = True`` in the ``live`` section, pywws will
use Weather Underground's 'Rapid Fire' mode to send a reading every 48
seconds.

Restart your regular pywws program (``Hourly.py`` or ``LiveLog.py``)
and visit the Weather Underground web site to see regular updates from
your weather station.

"""

__docformat__ = "restructuredtext en"
__usage__ = """
 usage: python ToUnderground.py [options] data_dir
 options are:
  -h or --help     display this help
  -c or --catchup  upload all data since last upload (up to 4 weeks)
  -v or --verbose  increase amount of reassuring messages
 data_dir is the root directory of the weather data
"""
__doc__ %= __usage__
__usage__ = __doc__.split('\n')[0] + __usage__

import getopt
import sys
from datetime import datetime, timedelta

import DataStore
from Logger import ApplicationLogger
import toservice

class ToUnderground(toservice.ToService):
    """Upload weather data to Weather Underground.

    """
    def __init__(self, params, calib_data):
        """

        :param params: pywws configuration.

        :type params: :class:`pywws.DataStore.params`
        
        :param calib_data: 'calibrated' data.

        :type calib_data: :class:`pywws.DataStore.calib_store`
    
        """
        toservice.ToService.__init__(
            self, params, calib_data, service_name='underground')

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "hcv", ['help', 'catchup', 'verbose'])
    except getopt.error, msg:
        print >>sys.stderr, 'Error: %s\n' % msg
        print >>sys.stderr, __doc__.strip()
        return 1
    # process options
    catchup = False
    verbose = 0
    for o, a in opts:
        if o == '-h' or o == '--help':
            print __doc__.strip()
            return 0
        elif o == '-c' or o == '--catchup':
            catchup = True
        elif o == '-v' or o == '--verbose':
            verbose += 1
    # check arguments
    if len(args) != 1:
        print >>sys.stderr, "Error: 1 argument required"
        print >>sys.stderr, __doc__.strip()
        return 2
    logger = ApplicationLogger(verbose)
    return ToUnderground(
        DataStore.params(args[0]), DataStore.calib_store(args[0])
        ).Upload(catchup)

if __name__ == "__main__":
    sys.exit(main())
