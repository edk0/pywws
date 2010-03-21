"""Localisation.py - provide translations of strings into local language"""

import gettext
import locale
import os
import sys

langs = []
#Check the default locale
lc, encoding = locale.getdefaultlocale()
if lc:
    langs = [lc, lc[:2]]
# Add one we know to be there
langs += ["en_GB", "en"]
trans = gettext.translation(
    'pywws', os.path.join(os.path.dirname(sys.argv[0]), 'locale'), languages=langs)
_ = trans.gettext
charset = trans._charset
if charset in (None, 'ASCII'):
    charset = 'iso-8859-1'
