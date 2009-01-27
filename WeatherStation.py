"""WeatherStation.py - get data from WH1080 compatible weather stations

Derived from wwsr.c by Michael Pendec (michael.pendec@gmail.com) and
wwsrdump.c by Svend Skafte (svend@skafte.net), modified by Dave Wells.
"""

import math
import usb

# calculate dew point
def dew_point(temp, hum):
    a = 17.27
    b = 237.7
    gamma = ((a * temp) / (b + temp)) + math.log(float(hum) / 100.0)
    return (b * gamma) / (a - gamma)

# convert wind direction integer to string
wind_dir_text = [
    'N', 'NNE', 'NE', 'ENE',
    'E', 'ESE', 'SE', 'SSE',
    'S', 'SSW', 'SW', 'WSW',
    'W', 'WNW', 'NW', 'NNW',
    ]

# convert pressure trend to a string
def pressure_trend_text(trend):
    if trend >= 0.1:
        result = 'rising'
    elif trend <= -0.1:
        result = 'falling'
    else:
        return 'steady'
    if abs(trend) > 6.0:
        return result + ' very rapidly'
    if abs(trend) > 3.5:
        return result + ' quickly'
    if abs(trend) <= 1.5:
        return result + ' slowly'
    return result

# get meaning for status integer
unknown         = 0x80
lost_connection = 0x40
unknown         = 0x20
unknown         = 0x10
unknown         = 0x80
unknown         = 0x40
unknown         = 0x20
unknown         = 0x10

# decode weather station raw data formats
def _decode(raw, offset):
    def _signed_short(raw, offset):
        lo = raw[offset]
        hi = raw[offset+1]
        if lo == 0xFF and hi == 0xFF:
            return None
        sign = 1
        if hi >= 128:
            sign = -1
            hi = hi - 128
        return sign * ((hi * 256) + lo)
    def _unsigned_short(raw, offset):
        lo = raw[offset]
        hi = raw[offset+1]
        if lo == 0xFF and hi == 0xFF:
            return None
        return (hi * 256) + lo
    def _bcd_decode(byte):
        hi = (byte / 16) & 0x0F
        lo = byte & 0x0F
        return (hi * 10) + lo
    def _date_time(raw, offset):
        year = _bcd_decode(raw[offset])
        month = _bcd_decode(raw[offset+1])
        day = _bcd_decode(raw[offset+2])
        hour = _bcd_decode(raw[offset+3])
        minute = _bcd_decode(raw[offset+4])
        return '%4d-%02d-%02d %02d:%02d' % (year + 2000, month, day, hour, minute)
    if not raw:
        return None
    if isinstance(offset, dict):
        result = {}
        for key, value in offset.items():
            result[key] = _decode(raw, value)
    else:
        pos, type, scale = offset
        if type == 'ub':
            result = raw[pos]
            if result == 0xFF:
                result = None
        elif type == 'us':
            result = _unsigned_short(raw, pos)
        elif type == 'ss':
            result = _signed_short(raw, pos)
        elif type == 'dt':
            result = _date_time(raw, pos)
        elif type == 'tt':
            result = '%02d:%02d' % (_bcd_decode(raw[pos]),
                                    _bcd_decode(raw[pos+1]))
        elif type == 'pb':
            result = raw[pos]
        else:
            raise IOError('unknown type %s' % type)
        if scale:
            result = float(result) * scale
    return result
# find a USB device by product and vendor id
def findDevice(idVendor, idProduct):
    for bus in usb.busses():
        for device in bus.devices:
            if device.idVendor == idVendor and device.idProduct == idProduct:
                return device
    return None
# class that represents the weather station to user program
class weather_station():
    def __init__(self):
        self.devh = None
        # _open_readw
        dev = findDevice(0x1941, 0x8021)
        if not dev:
            raise IOError("Weather station device not found")
        self.devh = dev.open()
        if not self.devh:
            raise IOError("Open device failed")
        try:
            self.devh.detachKernelDriver(0)
        except usb.USBError:
            # kernel driver is already detached. No problem
            pass
        self.devh.claimInterface(0)
        self.devh.setAltInterface(0)
        # _init_wread
        tbuf = self.devh.getDescriptor(1, 0, 0x12)
        tbuf = self.devh.getDescriptor(2, 0, 0x09)
        tbuf = self.devh.getDescriptor(2, 0, 0x22)
        self.devh.releaseInterface()
        self.devh.setConfiguration(1)
        self.devh.claimInterface(0)
        self.devh.setAltInterface(0)
        self.devh.controlMsg(usb.TYPE_CLASS + usb.RECIP_INTERFACE,
                             0xA, 0, timeout=1000)
        tbuf = self.devh.getDescriptor(0x22, 0, 0x74)
        # init variables
        self._fixed_block = None
        self._data_block = None
        self._data_pos = None
    def __del__(self):
        if self.devh:
            try:
                self.devh.releaseInterface()
            except usb.USBError:
                # interface was not claimed. No problem
                pass
        self.devh = None
    def inc_ptr(self, ptr):
        result = ptr + 0x10
        if result > 0xFFF0:
            result = 0x0100
        return result
    def dec_ptr(self, ptr):
        result = ptr - 0x10
        if result < 0x0100:
            result = 0xFFF0
        return result
    def get_raw_data(self, ptr, unbuffered=False):
        idx = ptr - (ptr % 0x20)
        if unbuffered or self._data_pos != idx:
            self._data_pos = idx
            self._data_block = self._read_block(idx)
        return self._data_block[ptr-idx:0x10+ptr-idx]
    def get_data(self, ptr, unbuffered=False):
        return _decode(self.get_raw_data(ptr, unbuffered), self.reading_offset)
    def current_pos(self):
        return _decode(self._read_block(0x0000), self.lo_fix_offset['current_pos'])
    def get_raw_fixed_block(self):
        if not self._fixed_block:
            self._read_fixed_block()
        return self._fixed_block
    def get_fixed_block(self, keys=[]):
        if not self._fixed_block:
            self._read_fixed_block()
        offset = self.fixed_offset
        # navigate down list of keys to get to wanted data
        for key in keys:
            offset = offset[key]
        return _decode(self._fixed_block, offset)
    def get_lo_fix_block(self):
        return _decode(self._read_block(0x0000) +
                       self._read_block(0x0020), self.lo_fix_offset)
    def _read_block(self, ptr):
        buf_1 = (ptr / 256) & 0xFF
        buf_2 = ptr & 0xFF;
        self.devh.controlMsg(usb.TYPE_CLASS + usb.RECIP_INTERFACE, 9,
                             [0xA1, buf_1, buf_2, 0x20, 0xA1, buf_1, buf_2, 0x20],
                             value=0x200, timeout=1000)
        return self.devh.interruptRead(0x81, 0x20, 1000)
    def _read_fixed_block(self):
        # get first line
        mempos_curr = 0x0000
        self._fixed_block = self._read_block(mempos_curr)
        # check for valid data
        if (self._fixed_block[0] == 0x55 and self._fixed_block[1] == 0xAA) or \
           (self._fixed_block[0] == 0xFF and self._fixed_block[1] == 0xFF):
            for mempos_curr in range(0x0020, 0x0100, 0x0020):
                self._fixed_block = self._fixed_block + self._read_block(mempos_curr)
        else:
            self._fixed_block = None
    # tables of "meanings" for raw weather station data
    reading_offset = {
        'delay'     : (0, 'ub', None),
        'hum_in'    : (1, 'ub', None),
        'temp_in'   : (2, 'ss', 0.1),
        'hum_out'   : (4, 'ub', None),
        'temp_out'  : (5, 'ss', 0.1),
        'pressure'  : (7, 'us', 0.1),
        'wind_ave'  : (9, 'ub', 0.1),
        'wind_gust' : (10, 'us', 0.1),
        'wind_dir'  : (12, 'ub', None),
        'rain'      : (13, 'us', 0.3),
        'status'    : (15, 'pb', None),
        }
    lo_fix_offset = {
        'read_period'   : (16, 'ub', None),
        'current_pos'   : (30, 'us', None),
        'rel_pressure'  : (32, 'us', 0.1),
        'abs_pressure'  : (34, 'us', 0.1),
        'date_time'     : (43, 'dt', None),
        }
    fixed_offset = {
        'read_period'   : (16, 'ub', None),
        'current_pos'   : (30, 'us', None),
        'rel_pressure'  : (32, 'us', 0.1),
        'abs_pressure'  : (34, 'us', 0.1),
        'date_time'     : (43, 'dt', None),
        'alarm'         : {
            'hum_in'        : {'hi' : (48, 'ub', None), 'lo'  : (49, 'ub', None)},
            'temp_in'       : {'hi' : (50, 'ss', 0.1), 'lo'  : (52, 'ss', 0.1)},
            'hum_out'       : {'hi' : (54, 'ub', None), 'lo'  : (55, 'ub', None)},
            'temp_out'      : {'hi' : (56, 'ss', 0.1), 'lo'  : (58, 'ss', 0.1)},
            'windchill'     : {'hi' : (60, 'ss', 0.1), 'lo'  : (62, 'ss', 0.1)},
            'dewpoint'      : {'hi' : (64, 'ss', 0.1), 'lo'  : (66, 'ss', 0.1)},
            'abs_pressure'  : {'hi' : (68, 'ss', 0.1), 'lo'  : (70, 'ss', 0.1)},
            'rel_pressure'  : {'hi' : (72, 'ss', 0.1), 'lo'  : (74, 'ss', 0.1)},
            'wind_ave'      : {'bft' : (76, 'ub', None), 'ms' : (77, 'ub', 0.1)},
            'wind_gust'     : {'bft' : (79, 'ub', None), 'ms' : (80, 'ub', 0.1)},
            'wind_dir'      : (82, 'ub', None),
            'rain'          : {'hour' : (83, 'us', 0.3), 'day'   : (85, 'us', 0.3)},
            'time'          : (87, 'tt', None),
            },
        'max'           : {
            'hum_in'        : {'val' : (98, 'ub', None), 'date'   : (141, 'dt', None)},
            'hum_out'       : {'val' : (100, 'ub', None), 'date'  : (151, 'dt', None)},
            'temp_in'       : {'val' : (102, 'ss', 0.1), 'date'  : (161, 'dt', None)},
            'temp_out'      : {'val' : (106, 'ss', 0.1), 'date'  : (171, 'dt', None)},
            'windchill'     : {'val' : (110, 'ss', 0.1), 'date'  : (181, 'dt', None)},
            'dewpoint'      : {'val' : (114, 'ss', 0.1), 'date'  : (191, 'dt', None)},
            'abs_pressure'  : {'val' : (118, 'us', 0.1), 'date'  : (201, 'dt', None)},
            'rel_pressure'  : {'val' : (122, 'us', 0.1), 'date'  : (211, 'dt', None)},
            'wind_ave'      : {'val' : (126, 'us', 0.1), 'date'  : (221, 'dt', None)},
            'wind_gust'     : {'val' : (128, 'us', 0.1), 'date'  : (226, 'dt', None)},
            'rain'          : {
                'hour'          : {'val' : (130, 'us', 0.3), 'date'  : (231, 'dt', None)},
                'day'           : {'val' : (132, 'us', 0.3), 'date'  : (236, 'dt', None)},
                'week'          : {'val' : (134, 'us', 0.3), 'date'  : (241, 'dt', None)},
                'month'         : {'val' : (136, 'us', 0.3), 'date'  : (246, 'dt', None)},
                'total'         : {'val' : (138, 'us', 0.3), 'date'  : (251, 'dt', None)},
                },
            },
        'min'           : {
            'hum_in'        : {'val' : (99, 'ub', None), 'date'   : (146, 'dt', None)},
            'hum_out'       : {'val' : (101, 'ub', None), 'date'  : (156, 'dt', None)},
            'temp_in'       : {'val' : (104, 'ss', 0.1), 'date'  : (166, 'dt', None)},
            'temp_out'      : {'val' : (108, 'ss', 0.1), 'date'  : (176, 'dt', None)},
            'windchill'     : {'val' : (112, 'ss', 0.1), 'date'  : (186, 'dt', None)},
            'dewpoint'      : {'val' : (116, 'ss', 0.1), 'date'  : (196, 'dt', None)},
            'abs_pressure'  : {'val' : (120, 'us', 0.1), 'date'  : (206, 'dt', None)},
            'rel_pressure'  : {'val' : (124, 'us', 0.1), 'date'  : (216, 'dt', None)},
            },
        }