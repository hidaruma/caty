# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
from caty.jsontools import tagged

def _print_value(val):
    print u"value=" + unicode(val)

class Counter(object):
    the_counter = None
    base_value = 0
    step_value = 1

    @classmethod
    def _initialize(cls, config):
        cls.base_value = config.get('baseValue', 0)
        cls.step_value = config.get('stepValue', 1)

    @classmethod
    def _finalize(cls):
        # 特にやることはない
        pass

    @classmethod
    def _create(cls, mode, param):
        # mode, paramは無視
        if cls.the_counter is None:
            cls.the_counter = Counter()
        return cls.the_counter
        
    def __init__(self):
        self._value = self.base_value

    def value(self):
        return self._value

    def inc(self):
        self._value += self.step_value
        _print_value(self._value)

    def dec(self):
        self._value -= self.step_value
        _print_value(self._value)

    def reset(self):
        self._value = self.base_value
        _print_value(self._value)
        
    def _begin(self):
        # 省略
        pass

    def _commit(self):
        # 省略
        pass

    def _cancel(self):
        # 省略
        pass

    def _dispose(self):
        pass

       
class MgInitialize(Command):
    def execute(self, config):
        Counter._initialize(config)
        return tagged(u'OK', None)

class MgFinalize(Command):
    def execute(self):
        Counter._finalize()
        return None

class MgCreate(Command):
    def execute(self, mode_param):
        mode, param = mode_param
        return Counter._create(mode, param)

class Value(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        return counter.value()

class Inc(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        counter.inc()
        return counter

class Dec(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        counter.dec()
        return counter

class Reset(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        counter.reset()
        return counter

class MgBegin(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        counter._begin()
        return counter

class MgCommit(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        counter._commit()
        return counter

class MgCancel(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        counter._cancel()
        return counter

class MgDispose(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        counter = self.arg0
        counter._dispose()
        return counter
