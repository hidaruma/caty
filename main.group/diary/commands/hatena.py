from caty.command import *
import string
import re
ent_headline = re.compile(r'(^\*[0-9]+\*)')
ent_tags = re.compile(r'(^\[[^\]]+?\])')

class EntriesFromDay(Command):
    def execute(self, day):
        r = []
        for ent in process_day(day):
            if ent is None:
                continue
            ent[u'dayTitle'] = day['title']
            ent[u'dayDate'] = day['date']
            r.append(ent)
        return r

def process_day(day):
    lines = iter(day[u'body'].strip().split('\n'))
    buff = []
    for line in lines:
        if ent_headline.match(line):
            if buff:
                yield process_ent(buff)
                buff = []
        buff.append(line)
    if buff:
        yield process_ent(buff)

def process_ent(buff):
    ent = {u'tags': []}
    headline = buff.pop(0)
    if not ent_headline.match(headline): #leading text
        return None
    _, ts, rest = ent_headline.split(headline)
    ent[u'id'] = int(ts.strip('*'))
    ent[u'created'] = ent[u'id']
    while ent_tags.match(rest):
        _, tag, rest = ent_tags.split(rest)
        ent[u'tags'].append(tag[1:-1])
    ent[u'title'] = rest
    ent[u'content'] = u'\n'.join(buff)
    return ent

class ToCreole(Command):
    def execute(self, text):
        self.ulist = re.compile('^\\+.*')
        self.olist = re.compile('^\\-.*')
        self.table = re.compile('^\\|.+')
        self.heading = re.compile('^\\*.+')
        self.quote_start = re.compile('^>>$')
        self.quote_end = re.compile('^<<$')
        self.pre_start = re.compile('^>\\|(\w*)\\|$')
        self.pre_end = re.compile('^\\|\\|<$')
        lines = iter(text.strip().split('\n'))
        r = []
        for line in lines:
            r.append(self.transform(line))
        return self.replace_html(u'\n'.join(r))

    def transform(self, line):
        if self.olist.match(line):
            n = 0
            for c in line:
                if c == '-':
                    n += 1
                else:
                    break
            return u'#' * n + line[n:]
        elif self.ulist.match(line):
            n = 0
            for c in line:
                if c == '+':
                    n += 1
                else:
                    break
            return u'*' * n + line[n:]
        elif self.heading.match(line):
            n = 0
            for c in line:
                if c == '*':
                    n += 1
                else:
                    break
            return u'=' * n + line[n:]
        elif self.table.match(line):
            return line.replace('|*', '|=')
        elif self.quote_start.match(line):
            return u'|>>'
        elif self.quote_end.match(line):
            return u'|<<'
        elif self.pre_start.match(line):
            m = self.pre_start.match(line)
            if m.group(1):
                return u'{{{:code:lang=' + m.group(1)
            else:
                return u'{{{'
        elif self.pre_end.match(line):
            return u'}}}'
        else:
            return line

    def replace_html(self, src):
        hr = HTMLReplacer()
        hr.feed(src)
        return hr.text

class HTMLReplacer(object):
    OPENING_MAP = {
        'h1': u'=',
        'h2': u'==',
        'h3': u'===',
        'h4': u'====',
        'h5': u'=====',
        'h6': u'======',
        'a': u'[[',
        'img': u'{{',
        'strong': u'**',
        'em': u'//',
        'span': u'[[[',
        'b': u'**:b ',
        'del': u'[[[:del ',
        'ins': u'[[[:ins ',
        'code': u'{{{:code ',
        'i': u'//:i ',
        's': u'[[[:s ',
        'sub': u',,',
        'sup': u'^^',
        'pre': u'{{{',
        'div': u'[[[',
        'hr': u'----',
        'br': u'\\\\',
    }

    CLOSING_MAP = {
        'h1': u'',
        'h2': u'',
        'h3': u'',
        'h4': u'',
        'h5': u'',
        'h6': u'',
        'a': u']]',
        'img': u'',
        'strong': u'**',
        'em': u'//',
        'span': u']]]',
        'b': u'**',
        'del': u']]]',
        'ins': u']]]',
        'code': u'}}}',
        'i': u'//',
        's': u']]]',
        'sub': u',,',
        'sup': u'^^',
        'pre': u'}}}',
        'div': u']]]',
        'hr': u'',
        'br': u'',
    }
    
    def __init__(self):
        self.buff = []

    @property
    def text(self):
        return u''.join(self.buff)

    def feed(self, src):
        citer = iter(src)
        for c in citer:
            if c == u'<':
                self.process_element(citer)
            elif c == u'&':
                self.process_charref(citer)
            else:
                self.buff.append(c)
        
    def process_element(self, iterable):
        buff = []
        closing = False
        start_end = False
        for c in iterable:
            if c == u'/':
                if not buff:
                    closing = True
                else:
                    buff.append(c)
            elif c == u'>': # end of element
                break
            elif c == u'<': # not a element
                self.buff.append(u'<')
                self.buff.extend(buff)
                self.buff.append(u'<')
                buff = []
                break
            else:
                buff.append(c)
        if not buff:
            return
        if len(buff) >= 2 and buff[-1] == u'/':
            start_end = True
        biter = iter(buff)
        elemname = self.process_tagname(biter)
        if not elemname:
            self.buff.append(u'<')
            self.buff.extend(buff)
            return
        attrs = self.process_attrs(biter)
        if attrs is None:
            self.buff.append(u'<')
            self.buff.extend(buff)
            return
        if start_end:
            self.buff.append(self.attrs_to_str(elemname, attrs))
            self.buff.append(self.CLOSING_MAP[elemname])
            return
        elif closing:
            self.buff.append(self.CLOSING_MAP[elemname])
            return
        else:
            self.buff.append(self.attrs_to_str(elemname, attrs))
            return

    def process_tagname(self, iterable):
        buff = []
        for c in iterable:
            if c in string.ascii_letters:
                buff.append(c)
            else:
                break
        name = ''.join(buff)
        if name not in self.OPENING_MAP:
            return None
        else:
            return name

    def process_attrs(self, iterable):
        attrs = [[None, None]]
        buff = []
        for c in iterable:
            if c == '=':
                if buff:
                    attrs.append([''.join(buff).strip(), None])
                    buff = []
                if attrs[-1][1] is not None: # error case
                    return
                val = self.process_attr_value(iterable)
                if val is None:
                    return
                attrs[-1][1] = val
            elif c == '>':
                break
            elif c == ' ':
                pass
            else:
                if c not in string.ascii_letters: # not a attr name:
                    return
                else:
                    buff.append(c)
        return attrs[1:]

    def process_attr_value(self, iterable):
        state = u'ready'
        buff = []
        for c in iterable:
            if c == u' ':
                if state == u'ready':
                    pass
                else:
                    buff.append(c)
            elif c == u'"':
                if state == u'ready':
                    state = u'start'
                elif state == u'start':
                    break
            else:
                buff.append(c)
        return ''.join(buff)

    def attrs_to_str(self, elem, attrs):
        buff = []
        if elem == u'a':
            for k, v in attrs:
                if k == u'target':
                    buff.append(u'[[>')
                    break
            else:
                buff.append(u'[[')
            for k, v in attrs:
                if k == u'href':
                    buff.append(v)
                    buff.append(u'|')
                    break
        elif elem == u'img':
            buff.append(u'{{')
            found = False
            for k, v in attrs:
                if k not in ('src', 'alt'):
                    buff.append(u':'+k+u'='+v)
                    found = True
            if found:
                buff.append(u' ')
            for k, v in attrs:
                if k == u'src':
                    buff.append(v)
                    break
            for k, v in attrs:
                if k == u'alt':
                    buff.append(u'|')
                    buff.append(v)
                    break
            buff.append(u'}}')
        elif elem == u'br':
            buff.append(u'\\\\')
        elif elem == u'hr':
            buff.append(u'----')
        else:
            if not attrs:
                buff.append(self.OPENING_MAP[elem])
            else:
                buff.append(self.OPENING_MAP[elem].strip())
            for k, v in attrs:
                if k == u'class':
                    for s in v.split(u' '):
                        buff.append(u':'+s)
            for k, v in attrs:
                if k == u'class':
                    continue
                else:
                    buff.append(u':'+k+u'='+v)
        if attrs and elem not in (u'a', u'img'):
            buff.append(u' ')
        return u''.join(buff)

    def process_charref(self, iterable):
        buff = []
        refval = string.ascii_letters + string.digits
        for c in iterable:
            if c == ';':
                break
            elif c not in refval:
                self.buff.extend(buff)
                self.buff.append(c)
                return
            else:
                buff.append(c)
        ref = ''.join(buff)
        if ref.startswith('#x'):
            self.buff.append(unichr(int(ref[2:], 16)))
        elif ref.startswith('#'):
            self.buff.append(unichr(ref[1:]))
        else:
            if ref == 'gt':
                self.buff.append(u'>')
            elif ref == 'lt':
                self.buff.append(u'<')
            elif ref == 'amp':
                self.buff.append(u'&')
            elif ref == 'quot':
                self.buff.append(u'"')
            else:
                self.buff.extend(buff)
                self.buff.append(u';')
