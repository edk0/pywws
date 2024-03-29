"""
Calibrate raw weather station data
==================================

This module allows adjustment of raw data from the weather station as
part of the 'processing' step (see :doc:`pywws.Process`). For example,
if you have fitted a funnel to double your rain gauge's collection
area, you can write a calibration routine to double the rain value.

The default calibration does two things:
    #. Generate relative atmospheric pressure.
    #. Remove invalid wind direction values.
Any user calibration you write must also do these.

Writing your calibration module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Firstly, decide where you want to keep your module. Like your text and
graph templates, it's best to keep it separate from the pywws code, so
it isn't affected by pywws upgrades. I suggest creating a ``modules``
directory in the same place as your ``templates`` directory.

Create a plain text file in your ``modules`` directory, e.g.
``calib.py`` and copy the following text into it::

    class Calib(object):
        def __init__(self, params):
            self.pressure_offset = eval(params.get('fixed', 'pressure offset'))
        def calib(self, raw):
            result = dict(raw)
            # sanitise data
            if result['wind_dir'] is not None and result['wind_dir'] >= 16:
                result['wind_dir'] = None
            # calculate relative pressure
            result['rel_pressure'] = raw['abs_pressure'] + self.pressure_offset
            return result

The :class:`Calib` class has two methods. :py:meth:`Calib.__init__` is
the constructor and is a good place to set any constants you need.
:py:meth:`Calib.calib` generates a single set of 'calibrated' data
from a single set of 'raw' data. There are a few rules to follow when
writing this method:

    - Make sure you include the line ``result = dict(raw)``, which
      copies all the raw data to your result value, at the start.

    - Don't modify any of the raw data.

    - Make sure you set ``result['rel_pressure']``.

    - Don't forget to ``return`` the result at the end.

When you've finished writing your calibration module you can get pywws
to use it by putting its location in your ``weather.ini`` file. It
goes in the ``[paths]`` section, as shown in the example below::

    [paths]
    work = /tmp/weather
    templates = /home/jim/weather/templates/
    graph_templates = /home/jim/weather/graph_templates/
    user_calib = /home/jim/weather/modules/usercalib

Note that the ``user_calib`` value need not include the ``.py`` at the
end of the file name.

"""

__docformat__ = "restructuredtext en"

from datetime import datetime, timedelta
import logging
import os
import sys

class DefaultCalib(object):
    """Default calibration class.

    This class sets the relative pressure, using a pressure offset
    read from the weather station, and 'sanitises' the wind direction
    value. This is the bare minimum 'calibration' required.

    """
    def __init__(self, params):
        self.pressure_offset = eval(params.get('fixed', 'pressure offset'))
    def calib(self, raw):
        result = dict(raw)
        # sanitise data
        if result['wind_dir'] is not None and result['wind_dir'] >= 16:
            result['wind_dir'] = None
        # calculate relative pressure
        result['rel_pressure'] = raw['abs_pressure'] + self.pressure_offset
        return result

usercalib = None

class Calib(object):
    """Calibration class that implements default or user calibration.

    Other pywws modules use this method to create a calibration
    object. The constructor creates either a default calibration
    object or a user calibration object, depending on the
    ``user_calib`` value in the ``[paths]`` section of the ``params``
    parameter. It then adopts the calibration object's
    :py:meth:`calib` method as its own.

    """
    def __init__(self, params):
        global usercalib
        self.logger = logging.getLogger('pywws.Calib')
        user_module = params.get('paths', 'user_calib', None)
        if user_module:
            self.logger.info('Using user calibration')
            if not usercalib:
                path, module = os.path.split(user_module)
                sys.path.insert(0, path)
                module = os.path.splitext(module)[0]
                usercalib = __import__(
                    module, globals(), locals(), ['Calib'])
            self.calibrator = usercalib.Calib(params)
        else:
            self.logger.info('Using default calibration')
            self.calibrator = DefaultCalib(params)
        self.calib = self.calibrator.calib
