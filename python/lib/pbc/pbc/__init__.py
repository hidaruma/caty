u"""programming by contract
"""

class PbcObject(object):
    def __init__(self):
        self.__initialized = True
        self.__invariant__()

    @property
    def pbc_initialized(self):
        if hasattr(self, '_PbcObject__initialized'):
            return self.__initialized
        return False

    def preserve_properties(self):
        o = {}
        for n in self.__properties__:
            o[n] = getattr(self, n)
        return OldObject(o)

    def __invariant__(self):
        pass

    __properties__ = []

class OldObject(object):
    def __init__(self, old):
        self.__old = old

    def __getattr__(self, name):
        return self.__old[name]

class Contract(property):
    def __init__(self, f):
        property.__init__(self, lambda obj: lambda *args, ** kwds: self.execute(obj, *args, **kwds))
        self.require = PreCondition()
        self.ensure = PostCondition()
        self.body = f
    
    def execute(self, obj, *args, **kwds):
        if obj.pbc_initialized:
            old = obj.preserve_properties()
            obj.__invariant__()
            self.require.assert_condition(obj, *args, **kwds)
            assert isinstance(old, OldObject)
        r = self.body(obj, *args, **kwds)
        if obj.pbc_initialized:
            self.ensure.assert_condition(obj, r, old, *args, **kwds)
            obj.__invariant__()
        return r

    __call__  = execute

class Condition(object):
    def __init__(self):
        self.__conditions = []

    def __iadd__(self, func):
        self.__conditions.append(func)
        return self

    @property
    def conditions(self):
        return self.__conditions

class PreCondition(Condition):
    def assert_condition(self, obj, *args, **kwds):
        for a in self.conditions:
            a(obj, *args, **kwds)

class PostCondition(Condition):
    def assert_condition(self, obj, result, old, *args, **kwds):
        for a in self.conditions:
            a(obj, result, old, *args, **kwds)

