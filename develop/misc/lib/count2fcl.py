# -*- coding: utf-8 -*- 
#
#  count2fcl
#
def _print_value(val):
    print u"value=" + unicode(val)

class Counter(object):
    counters = {}
    # 設定値
    base_value = 0
    step_value = 1

    @classmethod
    def initialize(cls, app_instance, 
                    config):
    	if config is None:
            config={}
        cls.base_value = config.get('baseValue', 0)
        cls.step_value = config.get('stepValue', 1)
        print u"Hello, Initialized"
        return None # 成功のときはNone（Catyではnull）

    @classmethod
    def finalize(cls, app_instance):
        cls.counters = {}
        return None

    @classmethod
    def create(cls, app_instance, 
                system_param, mode, user_param):
        n = user_param
        c = cls.counters.get(n, None)
        if not c:
            # トップレベルカウンターを生成
            cls.counters[n] = Counter(None, cls.base_value)
        return cls.counters[n]
        
    @classmethod
    def list(cls):
        return cls.counters.keys()
        
    def __init__(self, parent, value):
        self.parent = parent
        self._value = value
        self.orig = value

    def value(self):
        return self._value

    def inc(self):
        self._value += Counter.step_value
        _print_value(self._value)

    def dec(self):
        self._value -= Counter.step_value
        _print_value(self._value)

    def reset(self):
        self._value = Counter.base_value
        _print_value(self._value)
        

    def start(self):
        return Counter(self, self._value)

    def commit(self):
        self.parent._value = self._value


    def cancel(self):
        self._value = self.orig

    def cleanup(self):
        pass

