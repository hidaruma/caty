# Classes and functions for tokenizing and parsing text.
import re
import types

class ParseError(Exception):
    def __init__(self, cs, caused_obj, message=''):
        self.pos = cs.pos
        self.cs = cs
        self.cause = caused_obj
        self._error_message = message

    @property
    def _message(self):
        self.cs.pos = self.pos
        line = self.cs.line
        col = self.cs.col
        while self.cs.pos > 0 and self.cs.current not in ('\r', '\n'):
            self.cs.back()
        
        start = self.cs.pos
        self.cs.next()
        while not self.cs.eof and self.cs.current not in ('\r', '\n'):
            self.cs.next()
        t = self.cs.text[start:self.cs.pos]
        spaces = ' ' * (col - 1) + '^'
        text = t + '\n' + spaces
        r = u'\nLine %d, Col %d:\n%s \nCaused by:%s' % (line, col, text, self._to_str(self.cause))
        if self._error_message:
            r = self._error_message + '\n' + r
        return r

    @property
    def message(self):
        return self._message

    def __str__(self):
        return str(self._message)

    def __unicode__(self):
        return self._message

    def _to_str(self, obj):
        if isinstance(obj, list):
            r = []
            for o in obj:
                r.append(self._to_str(o))
            return '[%s]' % (', '.join(r))
        else:
            return repr(obj)

class ParseFailed(ParseError):
    pass

class EndOfBuffer(ParseFailed):
    pass

class Parser(object):
    def __call__(self, seq):
        raise NotImplementedError()

    def run(self, text, **options):
        cs = CharSeq(text, **options)
        return cs.parse(self)

class Regex(object):
    def __init__(self, pattern, *options, **optkwds):
        self.pattern = pattern
        self.regex = re.compile(pattern, *options, **optkwds)

    def match(self, text):
        return self.regex.match(text)

class ParserHook(object):
    def __init__(self, *hooks):
        self.hooks = hooks

    def hook(self, parser):
        for h in self.hooks:
            h(parser)

    def __repr__(self):
        return 'Hook:' + repr(self.hooks)

class Location(object):
    def __init__(self, location_info, lineno, colno):
        self._location_info = location_info
        self._lineno = lineno
        self._colno = colno

    def __str__(self):
        if self._location_info is not None:
            return '%s: Line %d, Col %d' % (str(self._location_info), self._lineno, self._colno)
        else:
            return 'Line %d, Col %d' % (self._lineno, self._colno)

class CharSeq(object):
    def __init__(self, text, auto_remove_ws=False, 
                             hook=None, 
                             ws_char=[' ', '\t', '\r', '\n'], 
                             suppress_eof=False,
                             location_info=None):
        self.text = text
        self.pos = 0
        self.length = len(text)
        self.cursor = []
        if auto_remove_ws:
            ws = SkipWs(ws_char)
        self._method_cache = {}
        self.ws_char = set(ws_char)
        self.ignore_hook = False
        self.parser_hook = None
        if hook:
            self.parser_hook = ParserHook(hook) if not auto_remove_ws else ParserHook(ws, hook)
        else:
            if auto_remove_ws:
                self.parser_hook = ParserHook(ws)
        self._auto_remove_ws = auto_remove_ws
        self._hook = hook
        self._suppress_eof = suppress_eof
        self._location_info = location_info

    def clone(self):
        return CharSeq(
            self.text,
            self._auto_remove_ws,
            self._hook,
            self.ws_char
        )

    def __iter__(self):
        return self

    def next(self):
        if self.length <= self.pos:
            raise StopIteration()
        self.pos += 1
        return self.current

    def back(self):
        if self.pos == 0: return self.current
        self.pos -= 1
        return self.current

    @property
    def col(self):
        p = 0
        c = 0
        for i in range(self.pos):
            p += 1
            c += 1
            if self.is_linebreak(p):
                c = 0
        return c
    
    @property
    def line(self):
        p = 0
        l = 1
        for i in range(self.pos):
            p += 1
            if self.is_linebreak(p):
                l += 1
        return l

    @property
    def current(self):
        if self.eof: return ''
        return self.text[self.pos]

    def is_linebreak(self, pos):
        if pos >= self.length: return False
        if self.text[pos] == '\n':
            if pos > 0 and self.text[pos - 1] == '\r':
                return False
            else:
                return True
        elif self.text[pos] == '\r':
            return True
    
    @property
    def rest(self):
        return self.text[self.pos:]
    
    @property
    def eof(self):
        return self.length <= self.pos

    def set_cursor(self):
        self.cursor.append(self.pos)

    def delete_cursor(self):
        self.cursor.pop(-1)

    def rollback(self):
        self.pos = self.cursor.pop(-1)

    def matches(self, c):
        return self.rest.startswith(c)

    def parse(self, p):
        if self.parser_hook and not self.ignore_hook:
            self.ignore_hook = True
            self.parser_hook.hook(self)
            self.ignore_hook = False
        try:
            r = self._get_parser(p)(p)
        except ParseFailed, e:
            if self.eof and not self._suppress_eof:
                raise EndOfBuffer(self, e.cause)
            else:
                raise
        if not self.eof and self.parser_hook and not self.ignore_hook:
            self.ignore_hook = True
            self.parser_hook.hook(self)
            self.ignore_hook = False
        return r

    def _get_parser(self, p):
        c = p.__class__
        if c in self._method_cache:
            return self._method_cache[c]
        if isinstance(p, basestring):
            r = self._str
        elif isinstance(p, (list, tuple)):
            r = self._list
        elif isinstance(p, Regex):
            r = self._regex
        elif isinstance(p, Parser):
            r = self._parser
        elif isinstance(p, types.FunctionType):
            r = self._fun
        elif isinstance(p, types.MethodType):
            r = self._method
        self._method_cache[c] = r
        return r

    def _str(self, token):
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
        else:
            raise ParseFailed(self, token)
        return token

    def _regex(self, reg):
        t = self.text[self.pos:]
        m = reg.match(t)
        if not m:
            raise ParseFailed(self, reg)
        r = m.group(0)
        self.pos += len(r)
        return r

    def _list(self, ps):
        error_list = []
        for p in ps:
            try:
                r = self.parse(p)
            except EndOfBuffer, e:
                raise
            except ParseFailed, e:
                error_list.append(e)
            else:
                return r
        error_list.sort(cmp=lambda a, b:cmp(a.pos, b.pos))
        raise error_list[-1]

    def _parser(self, p):
        return p(self)

    def _fun(self, p):
        return p(self)

    def _method(self, p):
        return p(self)

    def peek(self, p):
        pos = self.pos
        try:
            return self.parse(p)
        finally:
            self.pos = pos

    def readline(self):
        s = self.parse(until('\n'))
        if self.eof:
            return s
        else:
            s += self.current
            self.next()
            return s

    @property
    def location(self):
        return Location(self._location_info, self.line, self.col)

def tolist(f):
    def _join(*args, **kwds):
        return list(f(*args, **kwds))
    return _join

class many(Parser):
    def __init__(self, parser):
        self.parser = parser
    
    @tolist
    def __call__(self, seq):
        try:
            while True:
                yield seq.parse(self.parser)
        except ParseFailed, e:
            pass

class many1(many):
    @tolist
    def __call__(self, seq):
        yield seq.parse(self.parser)
        for r in many.__call__(self, seq):
            yield r

class option(Parser):
    def __init__(self, parser, default=None):
        self.parser = parser
        self.default = default

    def __call__(self, seq):
        try:
            p = seq.pos
            return seq.parse(self.parser)
        except ParseFailed, e:
            if p == seq.pos:
                return self.default
            else:
                raise

import string
_KEYWORD_CHARS = set(string.ascii_letters + '_')
class keyword(Parser):
    def __init__(self, s, chars=_KEYWORD_CHARS):
        self._token = s
        self._chars = chars

    def __call__(self, seq):
        h = seq.ignore_hook
        seq.ignore_hook = True
        try:
            r = seq.parse(self._token)
            if seq.current in self._chars:
                raise ParseFailed(seq, self)
            if not h and seq.parser_hook:
                seq.parser_hook.hook(seq)
            return r
        finally:
            seq.ignore_hook = h

class satisfy(Parser):
    def __init__(self, cond):
        self.cond = cond

    def __call__(self, seq):
        if not self.cond(seq.current):
            raise ParseFailed(seq, self.cond)
        r = seq.current
        seq.next()
        return r

class until(Parser):
    def __init__(self, s):
        self.parser = s

    def __call__(self, seq):
        if isinstance(self.parser, basestring):
            p = seq.text.find(self.parser, seq.pos)
            if p == -1:
                s = seq.rest
                seq.pos = seq.length
                return s
            else:
                s = seq.rest[0:p - seq.pos]
                seq.pos += (p - seq.pos)
                return s
        else:
            pos_list = []
            for parser in self.parser:
                p = seq.text.find(parser, seq.pos)
                if p != -1:
                    pos_list.append(p)

            if pos_list:
                pos_list.sort()
                s = seq.rest[0:pos_list[0] - seq.pos]
                seq.pos += (pos_list[0] - seq.pos)
                return s
            s = seq.rest
            seq.pos = seq.length
            return s

class chainl(Parser):
    def __init__(self, parser, op, allow_trailing_operator=False):
        self.parser = parser
        self.op = op
        self.allow_trailing_operator = allow_trailing_operator

    def __call__(self, seq):
        def tail(l):
            try:
                o = seq.parse(self.op)
            except ParseFailed:
                return l
            try:
                r = seq.parse(self.parser)
            except ParseFailed:
                if self.allow_trailing_operator:
                    return l
                else:
                    raise
            return tail(o(l, r))
        return tail(seq.parse(self.parser))

class CombinedParser(Parser):
    def __init__(self, parsers):
        self.parsers = parsers
    
    @tolist
    def __call__(self, seq):
        while not seq.eof:
            for p in self.parsers:
                try:
                    r = p(seq)
                except ParseFailed, e:
                    pass
                else:
                    yield r
                    break
            else:
                raise ParseFailed(seq, self.parsers)

def combine(*components):
    return CombinedParser(components)

def as_parser(f):
    class Wrapper(Parser):
        def __init__(self, parser):
            self.parser = parser
            self.__name__ = parser.__name__
            self.__doc__ = parser.__doc__

        def __call__(self, seq):
            return self.parser(seq)

        def __repr__(self):
            return repr(self.parser)

    return Wrapper(f)

def normalize_lf(s):
    return s.strip().replace('\r\n', '\n').replace('\r', '\n')

class TryParser(Parser):
    def __init__(self, parser):
        self.parser = parser
        if hasattr(parser, '__name__'):
            self.__name__ = parser.__name__
        if hasattr(parser, '__doc__'):
            self.__doc__ = parser.__doc__

    def __call__(self, seq):
        seq.set_cursor()
        try:
            r = self.parser(seq)
        except ParseFailed, e:
            seq.rollback()
            raise 
        else:
            seq.delete_cursor()
            return r

    def __repr__(self):
        return repr(self.parser)

class SkipWs(Parser):
    def __init__(self, ws_char=[' ', '\t', '\r', '\n']):
        self.ws_char = set(ws_char)

    def __call__(self, seq):
        while seq.current in self.ws_char:
            seq.next()

skip_ws = SkipWs()

class choice(Parser):
    def __init__(self, *parsers):
        self._parsers = parsers

    def __call__(self, seq):
        return seq.parse(self._parsers)

def EOL(seq):
    if seq.eof:
        return u''
    return seq.parse([u'\r\n', u'\r', u'\n'])

class S(Parser):
    def __init__(self, s):
        self._s = s

    def __call__(self, seq):
        return seq.parse(self._s)

def try_(f):
    return TryParser(f)

class split(Parser):
    def __init__(self, parser, delim, allow_last_delim=False):
        self.parser = parser
        self.delim = delim
        self.allow_last_delim = allow_last_delim

    def __call__(self, seq):
        r = []
        r.append(seq.parse(self.parser))
        if seq.eof:
            return r
        while True:
            try:
                a = seq.parse(self.delim)
            except EndOfBuffer, e:
                raise
            except ParseFailed, e:
                break
            try:
                b = seq.parse(self.parser)
            except EndOfBuffer, e:
                raise
            except ParseFailed, e:
                if self.allow_last_delim:
                    break
                else:
                    raise
            else:
                r.append(b)
                if seq.eof:
                    break
        return r

class unordered(Parser):
    def __init__(self, *parsers):
        self.parsers = parsers

    def __call__(self, seq):
        return self.__parse(seq, list(self.parsers))

    def __parse(self, seq, parsers):
        error_list = []
        l = None
        for p in parsers:
            try:
                r = p(seq)
            except EndOfBuffer, e:
                raise
            except ParseFailed, e:
                if isinstance(p, mandatory):
                    error_list.append(e)
            else:
                l = p
                break
        else:
            if error_list:
                error_list.sort(cmp=lambda a, b:cmp(a.pos, b.pos))
                raise error_list[-1]
            else:
                return []
        parsers.remove(l)
        if parsers:
            return [r] + self.__parse(seq, parsers)
        else:
            return [r]

class mandatory(Parser):
    def __init__(self, parser):
        self.parser = parser

    def __call__(self, seq):
        return seq.parse(self.parser)

class peek(Parser):
    def __init__(self, parser):
        self.parser = parser

    def __call__(self, seq):
        return seq.peek(self.parser)

alpha = Regex(r'[a-zA-Z_]+')
number = Regex(r'[0-9]+')
alphanum = Regex(r'[a-zA-Z_0-9]+')

import topdown.test

