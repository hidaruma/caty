#coding:utf-8
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
            for i in v:
                self[k] = i#copy.deepcopy(i)

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


from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

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

