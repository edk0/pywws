#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Localisation.py - provide translations of strings into local
language

::

%s

Introduction
------------

Some of the pywws modules, such as WindRose.py, can automatically use
your local language for such things as wind directions. The
Localisation.py module, mostly copied from examples in the Python
documentation, enables this.

Localisation of pywws is done in two parts - translating strings such
as 'rising very rapidly', and changing the 'locale' which controls
things like month names and number representation (e.g. '23,2' instead
of '23.2'). On some computers it may not be possible to set the
locale, but translated strings can still be used.

Using a different language
--------------------------

The language used by pywws is set in the ``[config]`` section of the
``weather.ini`` file. This can be a two-letter language code, such as
``en`` (English), or can specify a national variant, such as ``fr_CA``
(Canadian French). It could also include a character set, for example
``de_DE.UTF-8``.

The choice of language is very system dependant, so Localisation.py
can be run as a standalone program to test language codes. A good
starting point might be your system's ``LANG`` environment variable,
for example::

    jim@brains:~/Documents/weather/devel$ echo $LANG
    en_GB.UTF-8
    jim@brains:~/Documents/weather/devel$ python pywws/Localisation.py -t en_GB.UTF-8
    Locale changed from (None, None) to ('en_GB', 'UTF8')
    Translation set OK
    Locale
      decimal point: 23.2
      date & time: Friday, 14 October (14/10/11 13:02:00)
    Translations
      'NNW' => 'NNW'
      'rising very rapidly' => 'rising very rapidly'
      'Rain at times, very unsettled' => 'Rain at times, very unsettled'
    jim@brains:~/Documents/weather/devel$

In most cases no more than a two-letter code is required::

    jim@brains:~/Documents/weather/devel$ python pywws/Localisation.py -t fr
    Locale changed from (None, None) to ('fr_FR', 'UTF8')
    Translation set OK
    Locale
      decimal point: 23,2
      date & time: vendredi, 14 octobre (14/10/2011 13:04:44)
    Translations
      'NNW' => 'NNO'
      'rising very rapidly' => 'en hausse très rapide'
      'Rain at times, very unsettled' => 'Quelques précipitations, très perturbé'
    jim@brains:~/Documents/weather/devel$

If you try an unsupported language, pywws falls back to English::

    jim@brains:~/Documents/weather/devel$ python pywws/Localisation.py -t ja
    Failed to set locale: ja
    No translation file found for: ja
    Locale
      decimal point: 23.2
      date & time: Friday, 14 October (10/14/11 13:08:49)
    Translations
      'NNW' => 'NNW'
      'rising very rapidly' => 'rising very rapidly'
      'Rain at times, very unsettled' => 'Rain at times, very unsettled'
    jim@brains:~/Documents/weather/devel$

Once you've found a suitable language code that works, you can
configure pywws to use it by editing your ``weather.ini`` file::

 [config]
 language = fr

Creating a new translation
--------------------------

If there is no translation file for your preferred language then you
need to create one. See :doc:`../guides/language` for detailed
instructions.

"""

__docformat__ = "restructuredtext en"

__usage__ = """
 usage: python pywws/Localisation.py [options]
 options are:
  -h       or  --help       display this help
  -t code  or  --test code  test use of a language code
"""

__doc__ %= __usage__
__usage__ = __doc__.split('\n')[0] + __usage__

import getopt
import gettext
import locale
import os
import sys
import time

# set translation to be used if SetTranslation is not called
translation = gettext.NullTranslations()

def SetLocale(lang):
    """Set the 'locale' used by a program.

    This affects the entire application, changing the way dates,
    currencies and numbers are represented. It should not be called
    from a library routine that may be used in another program.

    The ``lang`` parameter can be any string that is recognised by
    ``locale.setlocale()``, for example ``en``, ``en_GB`` or ``en_GB.UTF-8``.

    :param lang: language code.
    :type lang: string
    :return: success status.
    :rtype: bool

    """
    # get the default locale
    lc, encoding = locale.getdefaultlocale()
    try:
        if '.' in lang:
            locale.setlocale(locale.LC_ALL, lang)
        else:
            locale.setlocale(locale.LC_ALL, (lang, encoding))
    except locale.Error:
        return False
    return True

def SetTranslation(lang):
    """Set the translation used by (some) pywws modules.

    This sets the translation object ``Localisation.translation`` to
    use a particular language.

    The ``lang`` parameter can be any string of the form ``en``,
    ``en_GB`` or ``en_GB.UTF-8``. Anything after a ``.`` character is
    ignored. In the case of a string such as ``en_GB``, the routine
    will search for an ``en_GB`` language file before searching for an
    ``en`` one.

    :param lang: language code.
    :type lang: string
    :return: success status.
    :rtype: bool

    """
    global translation
    # make list of possible languages, in order of preference
    langs = list()
    if lang:
        if '.' in lang:
            lang = lang.split('.')[0]
        langs += [lang, lang[:2]]
    # get translation object
    path = os.path.join(os.path.dirname(sys.argv[0]), '..', 'locale')
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(sys.argv[0]), 'locale')
    try:
        translation = gettext.translation('pywws', path, languages=langs)
    except IOError:
        return False
    return True

def SetApplicationLanguage(params):
    """Set the locale and translation for a pywws program.

    This function reads the language from the configuration file, then
    calls :func:`SetLocale` and :func:`SetTranslation`.

    :param params: a :class:`pywws.DataStore.params` object.

    :type params: object

    """
    lang = params.get('config', 'language', None)
    if lang:
        SetLocale(lang)
        SetTranslation(lang)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "ht:", ['help', 'test='])
    except getopt.error, msg:
        print >>sys.stderr, 'Error: %s\n' % msg
        print >>sys.stderr, __usage__.strip()
        return 1
    # process options
    code = None
    for o, a in opts:
        if o in ('-h', '--help'):
            print __usage__.strip()
            return 0
        elif o in ('-t', '--test'):
            code = a
    # check arguments
    if len(args) != 0:
        print >>sys.stderr, 'Error: no arguments required\n'
        print >>sys.stderr, __usage__.strip()
        return 2
    # test language code
    if code:
        old_locale = locale.getlocale()
        if SetLocale(code):
            new_locale = locale.getlocale()
            print "Locale changed from", old_locale, "to", new_locale
        else:
            print "Failed to set locale:", code
        if SetTranslation(code):
            print "Translation set OK"
        else:
            print "No translation file found for:", code
    # try a few locale / translation effects
    print "Locale"
    print "  decimal point:", locale.format("%4.1f", 23.2)
    print "  date & time:", time.strftime("%A, %d %B (%x %X)")
    print "Translations"
    print "  'NNW' => '%s'" % (translation.lgettext('NNW'))
    print "  'rising very rapidly' => '%s'" % (
        translation.lgettext('rising very rapidly'))
    print "  'Rain at times, very unsettled' => '%s'" % (
        translation.lgettext('Rain at times, very unsettled'))
    return 0

if __name__ == "__main__":
    sys.exit(main())
