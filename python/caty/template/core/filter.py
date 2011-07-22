import types

class FilterError(Exception):
    def __init__(self, classname, typelist):
        self.msg = '%s: can not applicate %s to arguments type' % (classname, str(typelist))

    def __str__(self):
        return self.msg

class FilterContainer(object):
    def __init__(self):
        self._filters = {}
    def add(self, filter):
        self._filters[filter.name] = filter

    def get(self, name):
        return self._filters[name]

class AbstractFilter(object):
    def __call__(self,*arguments):
        return self.filter(*arguments)

    def filter(self, *args):
        raise NotImplementedError

    argc = property(lambda self: self.filter.func_code.co_argcount - 1)


class NotNullFilter(AbstractFilter):
    name = 'notnull'

    def filter(self, a):
        return a != None

class NotEmptyFilter(AbstractFilter):
    name = 'notempty'

    def filter(self, a):
        return a != [] and a != {} and a != '' and a != None

class EmptyFilter(AbstractFilter):
    name = 'empty'

    def filter(self, a):
        return a == [] or a == {} or a == '' or a == None

class ModuloFilter(AbstractFilter):
    name = 'mod'

    def filter(self, a, b):
        return a % a.__class__(b)

class EqFilter(AbstractFilter):
    name = 'eq'

    def filter(self, a, b):
        return a == b

class NotEqFilter(AbstractFilter):
    name = 'ne'

    def filter(self, a, b):
        return a != b

class UpperFilter(AbstractFilter):
    name = 'upper'

    def filter(self, a):
        return a.upper()

class LowerFilter(AbstractFilter):
    name = 'lower'

    def filter(self, a):
        return a.lower()

class NotFilter(AbstractFilter):
    name = 'not'
    def filter(self, b):
        return not b

import types
def get_filters():
    r = [f() for f in globals().values() if isinstance(f, types.TypeType) and issubclass(f, AbstractFilter) and f != AbstractFilter]
    return r



