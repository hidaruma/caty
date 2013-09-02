#coding: utf-8
from __future__ import with_statement
from threading import RLock
from caty.util.collection import *
from caty.util.cache import memoize
import caty.core.runtimeobject as ro
u"""共通的に使われるユーティリティ群。
"""
def try_parse(type, s, fallback=None):
    u"""s を type に変換する。
    失敗時にはfallbackを返す。
    """
    try:
        return type(str(s))
    except:
        return fallback

def try_parse_to_num(o):
    from decimal import Decimal
    return try_parse(int, o, try_parse(Decimal, o, o))

def bind1st(f, a):
    def bound(b):
        return f(a, b)
    return bound

def bind2nd(f, b):
    def bound(a):
        return f(a, b)
    return bound

def error_to_ustr(e):
    import sys
    v = float(sys.version.split(' ')[0].rsplit('.', 1)[0])
    from caty.core.exception import CatyException
    if isinstance(e, CatyException):
        return e.tag + u':' + e.get_message(ro.i18n)
    if v <= 2.5:
        return e.message if isinstance(e.message, unicode) else unicode(e.message, 'utf-8')
    else:
        try:
            return unicode(e)
        except:
            return unicode(repr(e))

def get_message(e, encoding):
    import sys
    v = float(sys.version.split(' ')[0].rsplit('.', 1)[0])
    if v <= 2.5:
        return e.message if not isinstance(e.message, unicode) else e.message.encode(encoding)
    else:
        try:
            if hasattr(e, 'filename'):
                return _encode(e.strerror, encoding) + ':' + _encode(e.filename, encoding)
            return _encode(e.strerror, encoding)
        except:
            try:
                return unicode(e).encode(encoding)
            except:
                return repr(e)
    
def _encode(s, encoding):
    if isinstance(s, unicode):
        return s.encode(encoding)
    else:
        return s

def to_unicode(val):
    if isinstance(val, unicode):
        return val
    elif isinstance(val, bool):
        return unicode(str(val)).lower()
    else:
        if val is not None:
            return unicode(str(val))

def get_charset(obj):
    import re
    matcher = re.compile('charset=(.+)')
    matched = matcher.search(obj['header']['content-type'])
    if matched:
        return matched.group(1)
    else:
        return None

def escape_html(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').replace('\'', '&#39;')

import sys, traceback
class ConsoleWriter(object):
    def __init__(self):
        self.encoding = None # 端末エンコーディングが指定される
        self._streams = [sys.stdout]

    @property
    def streams(self):
        return self._streams

    def set_encoding(self, encoding):
        self.encoding = encoding

    def _to_str(self, arg):
        from codecs import getencoder
        assert self.encoding is not None
        assert isinstance(arg, (unicode, Exception, str)) or arg is traceback, type(arg)
        if isinstance(arg, unicode):
            r = getencoder(self.encoding)(arg, 'replace')
            return r[0]
        elif isinstance(arg, Exception):
            return get_message(arg, self.encoding)
        elif isinstance(arg, str):
            return brutal_encode(arg, self.encoding).encode(self.encoding)
        else:
            try:
                tb = brutal_encode(traceback.format_exc(), self.encoding)
            except:
                tb = brutal_encode(traceback.format_exc(), 'cp932')
            return tb.encode(self.encoding)

    def write(self, arg):
        for stream in self.streams:
            stream.write(self._to_str(arg))
            stream.flush()

    def writeln(self, arg):
        for stream in self.streams:
            stream.write(self._to_str(arg))
            stream.write('\n')
            stream.flush()

class DebugWriter(ConsoleWriter):
    def write(self, arg):
        for stream in self.streams:
            stream.write('DEBUG: ')
            stream.write(self._to_str(arg))
            stream.flush()

    def writeln(self, arg):
        for stream in self.streams:
            stream.write('DEBUG: ')
            stream.write(self._to_str(arg))
            stream.write('\n')
            stream.flush()

cout = ConsoleWriter()
debug = DebugWriter()

def init_writer(encoding, logfile=None, elogfile=None):
    cout.set_encoding(encoding)
    debug.set_encoding(encoding)
    if logfile:
        cout.streams.append(logfile)
        debug.streams.append(logfile)
    if elogfile:
        debug.streams.append(elogfile)
    return cout, debug

def error_wrapper(f):
    def _(*args, **kwds):
        try:
            return f(*args, **kwds)
        except Exception, e:
            print traceback.format_exc()
            cout.write(error_to_ustr(e))
            raise
    return _


def deprecated(msg):
    def _deprecated(f):
        def func(*args, **kwds):
            traceback.print_stack()
            cout.writeln(u'DEPRECATED: ' + repr(f))
            cout.writeln('            ' + msg)
            return f(*args, **kwds)
        return func
    return _deprecated

class OptPrinter(object):
    def __init__(self):
        self._opts = []
        self._max_length = 0

    def add(self, opt, msg=None):
        self._opts.append((opt, msg))
        if msg:
            l = len(opt)
            if l > self._max_length:
                self._max_length = l

    def show(self):
        for o, m in self._opts:
            if m:
                print u'  %s%s  %s' % (o, ' '*(self._max_length - len(o)), self._format(o, m))
            else:
                print o

    def _format(self, o, m):
        ws_len = 4 + self._max_length
        if '\n' not in m:
            return m
        lines = m.split('\n')
        return '\n'.join([lines[0]] + map(lambda x: ' ' * ws_len + x, lines[1:]))


def brutal_encode(s, e, l=['utf-8', 'cp932', 'euc-jp', 'sjis', 'unicode-escape']):
    if isinstance(s, unicode):
        return s
    try:
        return unicode(s, e)
    except:
        if l:
            return brutal_encode(s, l[0], l[1:])
        else:
            raise

def brutal_error_printer(f):
    def _(*args, **kwds):
        try:
            return f(*args, **kwds)
        except Exception, e:
            cout.writeln(error_to_ustr(e))
            raise 
    return _

def indent_lines(target, indent):
    if isinstance(target, basestring):
        target = [s + '\n' for s in target.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    r = []
    for t in target:
        r.append(indent+t)
    return ''.join(r)

def justify_messages(seq):
    max_width = max(map(lambda x:len(x[0]), seq)) if seq else 0
    r = []
    for s in seq:
        r.append( (s[0].ljust(max_width + 1) + s[1]))
    return '\n'.join(r)

def utime_from_timestr(timestr, fmt=u'%Y%m%d%H%M'):
    import time
    return time.mktime(time.strptime(timestr, fmt))

def timestamp_from_utime(sec):
    import datetime
    import time
    return datetime.datetime(*(time.localtime(sec)[:-3]))

def normalize_tribool(a):
    from caty.core.spectypes import INDEF
    from caty.jsontools import tag
    if a == True or tag(a) in (u'True', u'OK'):
        return True
    elif a == False or tag(a) in (u'False', u'NG'):
        return False
    else:
        return INDEF

def DEBUG(a):
    print
    print u'[DEBUG]', a

