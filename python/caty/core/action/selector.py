#coding:utf-8
from topdown import *
from caty.core.exception import *
from caty.util.path import splitext, dirname, join
from caty.util.collection import merge_dict
from caty.core.action.resource import DefaultResource
from caty.core.action.entry import ResourceActionEntry
from caty.core.schema.base import Annotations
from caty.core.action.entry import ResourceActionEntry
EXISTS = 0
PARENT = 1
NO_CARE = 2

class ResourceSelector(object):
    u"""ファイル/ディレクトリに関連付けられた verb を返す。
    """
    def __init__(self, app):
        self._entries = {}
        self._app = app

    def add(self, resource_class):
        if not resource_class.module + ':' + resource_class.name in self._entries:
            self._entries[resource_class.module + ':' + resource_class.name] = PathMatcher(resource_class)
        else:
            self._entries[resource_class.module + ':' + resource_class.name].update(resource_class)

    def get(self, fs, path, verb, method, no_check=False):
        ext = splitext(path)[1]
        fname = path
        matched = []
        for e in self._entries.values():
            action = e.get(fs, path, verb, method, no_check)
            if action:
                matched.append(action)
        if not matched:
            return None
        else:
            matched.sort(cmp=lambda a, b:cmp(a.matcher.score, b.matcher.score))
            r = matched[0]
            if 'deprecated' in r.annotations:
                print '[DEPRECATED]', r.name, path, '%s/%s' % (verb, method)
            return r

    def update(self, another):
        for k, v in another._entries.items():
            if k not in self._entries:
                self._entries[k] = v
            else:
                self._entries[k].update(v.resource_class)

    def __repr__(self):
        return repr(self._entries)

    def get_resource(self, name):
        r = self._entries.get(name, None)
        if r:
            return r._resource_class
        else:
            return None

    def validate_url_patterns(self):
        pairs = set([frozenset([e1, e2]) for e1 in self._entries.values() for e2 in self._entries.values() if e1 != e2])
        for e1, e2 in pairs:
            if not e1.is_exclusive(e2):
                throw_caty_exception(u'ResourcePatternError', 
                                     u'$pattern1 and $pattern2 is not exclusive', 
                                     pattern1=e1._resource_class.canonical_name, 
                                     pattern2=e2._resource_class.canonical_name)

NOT_MATCHED = 0
PATH_MATCHED = 1
MATCHED = 2

class PathMatcher(object):
    def __init__(self, resource_class):
        self._entries = {}
        self._resource_class = resource_class
        for p in resource_class.url_patterns:
            self._entries[p] = VerbMatcher(p, resource_class)
        
    def get(self, fs, path, verb, method, no_check=False):
        for e in self._entries.values():
            action = e.get(fs, path, verb, method, no_check)
            if action:
                break
        return action

    def update(self, resource_class):
        for p in resource_class.url_patterns:
            if p not in self._entries:
                self._entries[p] = VerbMatcher(p, resource_class)
            else:
                self._entries[p].update(resource_class)

    def is_exclusive(self, another):
        for p1 in self._resource_class.url_patterns:
            for p2 in another._resource_class.url_patterns:
                if not self._is_exclusive_pattern(p1, p2):
                    return False
        return True

    def _is_exclusive_pattern(self, p1, p2):
        from caty.util.collection import filled_zip
        tokens1 = as_parser(self._split_pattern).run(p1)
        tokens2 = as_parser(self._split_pattern).run(p2)
        for ts in filled_zip(tokens1, tokens2):
            t1, t2 = ts
            if t1 != t2:
                if '/' in (t1, t2): # ディレクトリとファイルの比較
                    return True
                if not (t1 in ('**', '*') and t2 in ('**', '*')): # 共にglobでない
                    return True
        print '[DEBUG]', p1, p2
        return False

    def _split_pattern(self, seq):
        return many1(choice(S(u'/'), Regex(u'[^./*]+'), S('*'), S('**'), Regex(ur'\.[^./*]+')))(seq)

class VerbMatcher(object):
    u"""verb dispatch の記述を解析し、 verb と method に応じたスクリプトを返す。
    verb dispatch の構文は以下の規則に従う。

    vd ::= verb ("/" method) ("#" "exists-parent")
    verb ::= 任意のアルファベット
    method ::= "GET" | "POST" | "PUT"

    """

    def __init__(self, pattern, resource_class):
        self._verbs = {}
        self._matcher = PathMatchingAutomaton(pattern)
        self.resource_class = resource_class
        self.name = resource_class.name
        self.annotations = resource_class.annotations
        self.update(resource_class)

    def update(self, resource_class):
        self.resource_class = resource_class
        self.name = resource_class.name
        self.annotations += resource_class.annotations
        for k, v in resource_class.entries.items():
            verb, method, parent = verb_parser.run(k, auto_remove_ws=True)
            if not verb in self._verbs:
                self._verbs[verb] = {
                    method: {
                        'command': v,
                        'parent': parent
                    }
                }
            else:
                self._verbs[verb][method] = {
                    'command': v,
                    'parent': parent
                }

    def get(self, fs, path, verb, method, no_check=False):
        res, m, rae = self._get(fs, path, verb, method, no_check)
        return Action(self.resource_class, m, rae)

    def _get(self, fs, path, verb, method, no_check):
        if not self._matcher.match(path):
            return NOT_MATCHED, None, None
        m = self._verbs.get(verb, None)
        if m is None:
            if 'finishing' in self.annotations:
                return NOT_MATCHED, self._matcher, ResourceActionEntry(None, u'http:bad-request %%0 %s/%s' % (verb, method), u'not-matched')
            return PATH_MATCHED, None, None
        e = m.get(method.upper(), None)
        if e is None:
            if 'finishing' in self.annotations:
                return NOT_MATCHED, self._matcher, ResourceActionEntry(None, u'http:bad-request %%0 %s/%s' % (verb, method), u'not-matched')
            elif '__default__' in m:
                e = m['__default__']
            else:
                return PATH_MATCHED, None, None
        f = fs.opendir(path) if self._matcher.is_dir else fs.open(path)
        if not f.exists:
            if e['parent'] == PARENT and not no_check:
                p = dirname(path) + '/' if dirname(path) not in ('/', '') else '/'
                if p == path: # ディレクトリが渡された場合
                    p = p.rstrip('/').rsplit('/', 1)[0]
                pdir = fs.opendir(p)
                if pdir.exists:
                    return MATCHED, self._matcher, e['command']
            elif e['parent'] == NO_CARE or no_check:
                return MATCHED, self._matcher, e['command']
                
            return NOT_MATCHED, self._matcher, ResourceActionEntry(None, u'http:not-found %0', u'not-found')
        else:
            return MATCHED, self._matcher, e['command']

    def __repr__(self):
        return repr(self._verbs)

class Error(object):
    def get(self, fs, path, verb, method):
        raise IOError(path)

class Action(object):
    def __init__(self, ra, matcher, rae):
        self.name = rae.name if rae else u'_'
        self.resource_name = ra.name
        self.module_name = ra.module
        self.matcher = matcher
        self.resource_class_entry = rae
        self.annotations = rae.annotations if rae else Annotations([])
        self.resource_class = ra

    def __nonzero__(self):
        return bool(self.matcher)

    def __repr__(self):
        return '%s:%s' % (self.module, self.name)

@as_parser
def verb_parser(seq):
    v = seq.parse(option(verb, u''))
    m = seq.parse(option(method, u'GET'))
    e = seq.parse(option(parent, 0))
    if not seq.eof:
        raise CatyException(u'CARA_PARSE_ERROR', u'Unknown checker: $checker', checker=seq.rest)
    return v, m, e

def verb(seq):
    return seq.parse(Regex(u'[a-zA-Z0-9_-]*'))

def method(seq):
    return seq.parse([u'/GET', u'/POST', u'/PUT', u'/DELETE'])[1:]

def parent(seq):
    x = seq.parse(['#exists-parent', '#dont-care'])
    if x == '#exists-parent':
        return PARENT
    else:
        return NO_CARE

import re
class PathMatchingAutomaton(object):
    def __init__(self, s):
        pattern = s.strip()
        self.pattern = pattern
        self.absolute = pattern.startswith('/')
        pattern = re.sub(r'^\.', r'**.', pattern)
        self.regexp = pattern.replace('**', r'[^/]+').replace('*', r'[^./]+').replace('.', r'\.') + '$'
        if not self.regexp.startswith('/'):
            self.regexp = '/' + self.regexp
        if self.absolute:
            self.regexp = '^' + self.regexp
        self.matcher = re.compile(self.regexp)
        v = 1000
        if self.absolute:
            v -= 1000
        v += self.pattern.count('**') * 100
        v += self.pattern.count('*') * 1
        v -= self.pattern.count('/') * 10
        self.score = v
        self.is_dir = pattern.endswith('/')

    def match(self, path):
        return self.matcher.search(path)

    def __repr__(self):
        return repr(self.pattern)

