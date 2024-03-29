#coding:utf-8
from xjson import OrderedDict
class SortedList(list):
    u"""挿入した値が常にソートされているリスト。
    """
    def __init__(self, comparator=cmp):
        list.__init__(self)
        self.cmp = comparator

    def add(self, obj):
        self.append(obj)
        self.sort(cmp=self.cmp)

def fork(iterator, filter_func):
    u"""filter_func が True になるグループと False になるグループの二つにイテレータを分割する。
    戻り値の値は二要素のタプルであり、タプルの要素はリストである。

    >>> fork([0, 1, 2, 3, 4], lambda x: x % 2 == 0)
    ([0, 2, 4], [1, 3])
    """
    a = []
    b = []
    for i in iterator:
        if filter_func(i):
            a.append(i)
        else:
            b.append(i)
    return a, b

def merge_dict(a, b, conflict_mode='post'):
    u"""再帰的に辞書をマージしていく。
    conflict_mode は a, b でキーが重複する葉に対しての動作である。
    デフォルトでは 'post' が使われる。

    'post': b の値を使う
    'pre': a の値を使う
    'error': 例外を送出する

    関数オブジェクトを conflict_mode に渡すことも可能である。
    その関数は a[k] と b[k] の二つの値を引数として受け取れなければならない。
    関数の戻り値の値がマージ結果の値となる
    """
    def copy(value):
        if isinstance(value, dict):
            new = {}
            for k, v in value.items():
                new[k] = copy(v)
            return new
        elif isinstance(value, list):
            return value[:]
        else:
            return value
    n = {}
    for k, v in a.items():
        n[k] = copy(v)

    for k, v in b.items():
        if k in n:
            if isinstance(v, dict) and isinstance(n[k], dict):
                n[k] = merge_dict(n[k], v, conflict_mode)
            else:
                if conflict_mode == 'post':
                    n[k] = copy(v)
                elif conflict_mode == 'pre':
                    pass
                elif conflict_mode == 'error':
                    raise Exception('Conflict: %s' % str(k))
                elif callable(conflict_mode):
                    r = conflict_mode(n[k], v)
                    n[k] = copy(r)
                else:
                    raise Exception('Unknown mode: %s' % str(conflict_mode))
        else:
            n[k] = copy(v)
    return n

import copy
class MultiMap(object):
    def __init__(self):
        self.__dict = {}

    def to_dict(self):
        r = {}
        for k, v in self.__dict.items():
            if len(v) == 1:
                r[k] = v[0]
            else:
                r[k] = v
        return r

    def __setitem__(self, k, v):
        if not k in self.__dict:
            self.__dict[k] = [v]
        else:
            self.__dict[k].append(v)

    def __contains__(self, k):
        return k in self.__dict

    def __getitem__(self, k):
        return self.__dict[k]

    def keys(self):
        return self.__dict.keys()

    def values(self):
        return self.__dict.values()

    def items(self):
        return self.__dict.items()

    def update(self, o):
        for k, v in o.items():
            if isinstance(o, MultiMap):
                for i in v:
                    self[k] = i#copy.deepcopy(i)
            else:
                self[k] = v

    def get(self, k, default):
        return self.__dict.get(k, default)

    def __repr__(self):
        r = []
        for k, v in self.items():
            r.append('%s: %s' % (repr(k), repr(v)))
        return '{%s}' % ', '.join(r)

    def clear(self):
        self.__dict.clear()

    __str__ = __repr__

import operator
class ImmutableDict(dict):
    u"""dict が unhashable で memoize できないので、代わりのオブジェクトを作る。
    """
    def __init__(self, o):
        p = {}
        for k, v in o.items():
            if isinstance(v, dict):
                p[k] = ImmutableDict(v)
            else:
                p[k] = v
        dict.__init__(self, p)
        self.__hash = self._make_hash()

    def __setitem__(self, k, v):
        raise Exception('Immutable')

    def _make_hash(self):
        r = []
        for k, v in self.items():
            r.append('%s%s' % (repr(k), repr(v)))
        return hash(reduce(operator.add, r))

    def __hash__(self):
        return self.__hash

class Empty(object):
    def __repr__(self):
        return '<EMPTY>'

    def __str__(self):
        return repr(self)

def dict_diff(l, r):
    def _dict_diff(a, b):
        d = {}
        for k, v in a.items():
            if k not in b:
                d[k] = (v, Empty())
            else:
                v2 = b[k]
                if v != v2:
                    if isinstance(v, dict) and isinstance(v2, dict):
                        d[k] = dict_diff(v, v2)
                    else:
                        d[k] = (v, v2)
        return d
    def _reverse(x):
        y = {}
        for k, v in x.items():
            if isinstance(v, dict):
                y[k] = _reverse(v)
            else:
                y[k] = (v[1], v[0])
        return y
    d = _dict_diff(l, r)
    d2 = _reverse(_dict_diff(r, l))
    for k, v in d2.items():
        if isinstance(v, dict):
            d[k] = v
        else:
            d[k] = (v[1], v[0])
    return d


class OverlayedDict(dict):
    def __init__(self, default):
        self.scope = [default]

    def new_scope(self):
        self.scope.insert(0, {})

    def del_scope(self):
        self.scope.pop(0)

    def __setitem__(self, k, v):
        self.scope[0][k] = v

    def __getitem__(self, k):
        for s in self.scope:
            if k in s:
                return s[k]
        raise KeyError(k)

    def __delitem__(self, k):
        for s in self.scope:
            if k in s:
                del s[k]

    def pop(self, k):
        if k in self:
            r = self[k]
        del self[k]
        return r

    def get(self, k, default=None):
        for s in self.scope:
            if k in s:
                return s[k]
        return default

    def __contains__(self, k):
        return any(map(lambda d: k in d, self.scope))

    def has_key(self, k):
        return any(map(lambda d: k in d, self.scope))

    @property
    def current_scope(self):
        return self.scope[0]

    def __repr__(self):
        return repr(self.scope)

    def clone(self):
        from copy import deepcopy
        n = OverlayedDict({})
        n.scope = []
        for s in self.scope:
            n.scope.insert(0, deepcopy(s))
        return n

    def keys(self):
        r = []
        for s in self.scope:
            for k in s.keys():
                r.append(k)
        return r

    def values(self):
        r = []
        for s in self.scope:
            for k in s.values():
                r.append(k)
        return r

    def items(self):
        r = []
        for s in self.scope:
            for k in s.items():
                r.append(k)
        return r

def filled_zip(seq1, seq2, fill=None):
    r = []
    i = 0
    l1 = len(seq1)
    l2 = len(seq2)
    while True:
        if i >= l1:
            o1 = fill
        else:
            o1 = seq1[i]
        if i >= l2:
            o2 = fill
        else:
            o2 = seq2[i]
        if i >= l1 and i>= l2:
            break
        r.append((o1, o2))
        i += 1
    return r

def conditional_dict(func, base=None, **kwds):
    r = {}
    if base:
        for k, v in base.items():
            if func(k, v):
                r[unicode(k)] = v

    for k, v in kwds.items():
        if func(k, v):
            r[unicode(k)] = v
    return r

def flatten(seq):
    for e in seq:
        if isinstance(e, (list, tuple)):
            for s in flatten(e):
                yield s
        else:
            yield e

def int_dict_to_list(d):
    a = []
    for k in sorted(d.keys()):
        while len(a) < k:
            a.append(UNDEFINED)
        a.append(d[k])
    return a
