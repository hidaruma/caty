# coding:utf-8
from topdown import *
from decimal import Decimal
import re

#__all__ = ['annotation', 'name', 'comma', 'chain_flat', 'docstring', 'SchemaSyntaxError', 'remove_comment']

def name(seq):
    return seq.parse(Regex(r'(([a-zA-Z_][-a-zA-Z0-9_]*)|(\$))'))

def comma(seq):
    _ = seq.parse(',')
    return _

class chain_flat(Parser):
    def __init__(self, parser, op):
        self.parser = parser
        self.op = op

    def __call__(self, seq):
        r = []
        r.append(seq.parse(self.parser))
        while True:
            try:
                a = seq.parse(self.op)
            except ParseFailed, e:
                break
            else:
                #カンマへの対応のみなので、 op の結果は捨てる
                try:
                    b = seq.parse(self.parser)
                    r.append(b)
                except ParseFailed:
                    break
        return r

def docstring(seq):
    return many1(__docstring)(seq)[-1]

def __docstring(seq):
    h = seq.ignore_hook
    seq.ignore_hook = True
    try:
        seq.parse(skip_ws)
        seq.parse('/**')
        if option(peek('/'))(seq):
            seq.back()
            seq.back()
            seq.back() #コメントなので元の位置にカーソルを移動
            raise ParseFailed(seq, __docstring)
        doc = seq.parse(until('*/')).strip('\n')#Regex(r'/\*\*.+?\*/', re.S))[3:-2].strip('\n')
        seq.parse('*/')
        seq.parse(skip_ws)
        if seq.eof:
            return None
        r = []
        lines = [d.strip() for d in doc.splitlines()]
        space = 0
        if not lines:
            return u''
        for i in list(lines[0]):
            if i == ' ':
                space += 1
            else:
                break
        d = []
        for l in lines:
            l = l.replace(' '*space, '', 1)
            if l == '*':
                l = ''
            elif l.startswith('* '):
                l = l[2:]
            d.append(l)
        return u'\n'.join(d)
    finally:
        seq.ignore_hook = h

class SchemaSyntaxError(Exception):
    def __init__(self, exception):
        self.exception = exception

    def __str__(self):
        return str(self.exception)

    def __unicode__(self):
        return unicode(self.exception)

    def __repr__(self):
        return repr(self.exception)

from caty.jsontools.xjson import parsers, string, multiline_string, binary
def value(seq):
    return seq.parse([string, binary, boolean, number, integer, multiline_string])

def boolean(seq):
    b = seq.parse(['true', 'false'])
    if b == 'true':
        return True
    else:
        return False

def integer(seq):
    return int(seq.parse(Regex(r'-?[0-9]+')))

def number(seq):
    return Decimal(seq.parse(Regex(r'-?[0-9]+\.[0-9]+')))


def _is_doc_str(seq):
    _ = seq.parse(option(docstring))
    #return bool(_)
    if _:
        try:
            seq.parse(skip_ws)
            _comment(seq, None)
            seq.parse(skip_ws)
            return False
        except:
            return True
    return False

def _item(seq):
    def _annotation(seq):
        seq.parse('@')
        seq.parse('[')
        seq.parse(until(']'))
        seq.parse(']')
    seq.parse(option(_annotation))
    seq.parse(skip_ws)
    seq.parse([string, '*'])
    seq.parse(skip_ws)
    seq.parse(':')

from caty.util import bind2nd
def remove_comment(seq, doc_str_checker=_is_doc_str):
    many(bind2nd(_comment, doc_str_checker))(seq)

def _comment(seq, doc_str_checker):
    if seq.current != '/':
        raise ParseFailed(seq, _comment)
    if doc_str_checker:
        doc_str = seq.peek(doc_str_checker)
        if doc_str:
            raise ParseFailed(seq, _comment)
    s = seq.parse(['//', '/*{{{', '/*'])
    if s == '//':
        seq.parse([until('\n'), until('\r')])
        seq.parse(skip_ws)
    elif s == '/*{{{':
        c = seq.parse(until('}}}*/'))
        if not seq.parse(option('}}}*/')):
            raise ParseError(seq, '}}}*/')
        seq.parse(skip_ws)
    elif s == '/*':
        c = seq.parse(until('*/'))
        if not seq.parse(option('*/')):
            raise ParseError(seq, '*/')
        seq.parse(skip_ws)

from caty.core.schema.base import Annotations, Annotation
def annotation(seq):
    if seq.current != '@':
        return Annotations([])
    seq.parse('@')
    seq.parse('[')
    a = seq.parse(split(_annotation_item, ','))
    seq.parse(']')
    return Annotations(a)

def _annotation_item(seq):
    symbol = seq.parse(Regex(u'[a-zA-Z_][-a-zA-Z0-9_]*'))
    arg = seq.parse(option(_annotation_arg, None))
    return Annotation(symbol, arg)

def _annotation_arg(seq):
    op = seq.parse('(')
    value = seq.parse(parsers)
    cp = seq.parse(')')
    return value

def string_array(seq):
    seq.parse('[')
    values = seq.parse(split(string, ','))
    seq.parse(']')
    return values

class IGNORE: pass

def fragment_name(seq):
    S('#')(seq)
    name = seq.parse(Regex('[a-zA-Z_0-9][-0-9_a-zA-Z]*'))
    return name


# 名前トークンの仕様は以下のIssue及び記事を参考にすること。
# pub@specdocs:/NameSyntax.wiki
# https://bitbucket.org/project_caty/dev/issue/675
#

_name_start_base = u'[a-zA-Z_]'
_extend_name_start = unicode("""[\u00C0-\u00D6] | [\u00D8-\u00F6] | [\u00F8-\u02FF] | [\u0370-\u037D] | 
   [\u037F-\u1FFF] | [\u200C-\u200D] | [\u2070-\u218F] | 
   [\u2C00-\u2FEF] | [\u3001-\uD7FF] | [\uF900-\uFDCF] | 
   [\uFDF0-\uFFFD] """, 'unicode-escape')
_name_start = _name_start_base + u'|' + _extend_name_start
_ext_name = unicode('\u00B7 | [\u0300-\u036F] | [\u203F-\u2040]', 'unicode-escape')
_name_char = u'|'.join([_name_start, '-', '[0-9]', _ext_name])
_name_token_ptn = u'({0})({1})*'.format(_name_start, _name_char)
_identifier_ptn = _name_token_ptn + u'(\\.{0})*'.format(_name_token_ptn)
_mod_identifier_ptn = u'({0}:)?{1}'.format(_identifier_ptn, _identifier_ptn)
_app_identifier_ptn = u'({n}::({i}|:{n}))|({i})'.format(n=_name_token_ptn, i=_mod_identifier_ptn)
import re
def some_token(seq):
    return seq.parse(Regex(u'({0})+'.format(_name_char), re.X))

def name_token(seq):
    return seq.parse(Regex(_name_token_ptn, re.X))

def identifier_token(seq):
    return seq.parse(Regex(_identifier_ptn, re.X))

def identifier_token_m(seq):
    return seq.parse(Regex(_mod_identifier_ptn, re.X))

def identifier_token_a(seq):
    return seq.parse(Regex(_app_identifier_ptn, re.X))

def split_colon_dot_path(s, consider_context=True):
    c = CDPSplitter(consider_context)
    return c.run(s)

class BasicCDPSplitter(Parser):
    def __call__(self, seq):
        app_name = option(Regex(_name_token_ptn + '::', re.X))(seq)
        mod_name = option(Regex(_identifier_ptn + ':', re.X))(seq)
        name = option(identifier_token)(seq)
        if app_name:
            app_name = app_name.strip(':')
        if mod_name:
            mod_name = mod_name.strip(':')
        if not seq.eof:
            raise ParseFailed(seq, u'not a colon dot path: %s' % seq.text)
        return app_name, mod_name, name

class CDPSplitter(Parser):
    def __init__(self, consider_context=u'application'):
        self.__consider_cotext = consider_context

    def __call__(self, seq):
        app_name = option(Regex(_name_token_ptn + '::', re.X))(seq)
        mod_name = option(Regex(_identifier_ptn + '(:|\\.$)', re.X))(seq)
        content_name = option(identifier_token)(seq)
        if app_name:
            app_name = app_name.rstrip(':')
        if mod_name:
            mod_name = mod_name.rstrip(':.')
        if not seq.eof:
            raise ParseFailed(seq, u'not a colon dot path: %s' % seq.text)
        if not app_name and self.__consider_cotext: # ::がない場合かつコンテキストをみる
            if not mod_name: # : がない裸の名前でモジュールコンテキスト
                if u'.' not in content_name: # パッケージでもない
                    # これはモジュールやパッケージを探す文脈での曖昧な名前であり、app解釈
                    app_name = content_name
                    content_name = None
                else: # content_nameはパッケージを指しているのでmod_nameと入れ替え
                    mod_name = content_name.strip('.')
                    content_name = None
        elif not mod_name and content_name and self.__consider_cotext: # :がない場合かつコンテキストをみる
            mod_name = content_name.strip('.')
            content_name = None
        return app_name, mod_name, content_name

