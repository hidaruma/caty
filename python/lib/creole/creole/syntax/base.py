from topdown import *
from creole.tree import Element
import string
halfwidth_char = set(string.printable.replace(' ', '').replace('\t', '').replace('\r', '').replace('\n', '').replace('\x0b', '').replace('\x0c', ''))

class WikiParser(Parser):
    def __init__(self, element_factory=None):
        self._element_factory = element_factory if element_factory else Element

    def create_element(self, *args, **kwds):
        return self._element_factory(*args, **kwds)

class BlockParser(WikiParser):
    def __init__(self, syntax, factory=None):
        self.language = syntax.language
        self.inline = syntax.inline
        self.syntax= syntax
        WikiParser.__init__(self, factory)

    def _format(self, text):
        text = text.lstrip(' \t').rstrip('\r\t\n')
        if self.language == 'jp':
            lines = map(lambda x:x.lstrip(' '), text.split('\n'))
            r = []
            last = ''
            for l in lines:
                if l:
                    if last in halfwidth_char or l[0] in halfwidth_char:
                        r.append('\n')
                    r.append(l)
                    last = l[-1]
            return ''.join(r).strip('\n')
        return text

class InlineParser(WikiParser):

    def _enter(self, seq):
        t = []
        end = [u'~', self.end]
        while not seq.eof:
            s = seq.parse(until(end))
            t.append(s)
            if seq.eof:
                break
            s = seq.parse(end)
            if s == u'~':
                t.append(u'~')
                t.append(seq.current)
                seq.next()
            else:
                break
        text = ''.join(t)
        return text

import sys
def escape_tilda(t):
    if t == '~':
        return u''
    seq = list(_exact_split(t))
    r = ['dummy']
    for s in seq:
        if not s and not r[-1]:
            r.append(u'~')
        else:
            r.append(s)
    return u''.join(r[1:])

def _exact_split(t):
    chunk = []
    p = 0
    not_line_top = False
    pchar = ''
    for n, c in enumerate(t):
        if c == '~':
            yield t[p:n]
            if not_line_top and pchar=='~':
                yield u''
            p = n+1
        else:
            not_line_top= True
        pchar = c
    yield t[p:]
