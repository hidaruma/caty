# -*- coding: utf-8 -*- 
#
#  count4fcl -- count3fclから修正
# 
# 名前で識別される複数のカウンター・インスタンスを持てる。
# カウンターインスタンスが状態として保持するのは単一の整数値。
# 一旦生成されると、Catyが終了するまで存在する。
#
# 次のように宣言して使う。
# 
#   facility conterA = Counter with "A";
#
# ユーザーパラメータは使えない。

def _print_value(val):
    print u"value=" + unicode(val)

class Counter(object):
    # 生成済みのマスターインスタンス達
    # カウンター値はマスターインスタンスによってCaty終了時まで保持される
    counters = {}
    # 設定値
    base_value = 0
    step_value = 1

    initialized = False

    @classmethod
    def initialize(cls, app_instance, config=None):
        if cls.initialized:
            # テスト用に、
            # 複数回繰り返し初期化しても弊害がないようにしておく
            return
    	if config is None:
            config={}
        # 設定値をセットする
        cls.base_value = config.get('baseValue', 0)
        cls.step_value = config.get('stepValue', 1)
        cls.initialized = True
        print u"Counter facility initialized."

    @classmethod
    def finalize(cls, app_instance):
        if not cls.initialized:
            # テスト用に、
            # 複数回繰り返し初期化しても弊害がないようにしておく
            return
        # マスターインスタンスをクリア
        for name in cls.counters:
            cls.counters[name].cleanup()
        cls.counters = {}
        cls.initialized = False
        print u"Counter facility finalized."

    @classmethod
    def instance(cls, app_instance, system_param=u"default"):
        # システムパラメータがカウンターの名前となる
        name = system_param
        c = cls.counters.get(name, None)
        if not c:
            # マスターインスタンスを新規生成
            c = cls.counters[name] = Counter(app_instance, name)
        return c

    @classmethod
    def is_ready(cls):
        return cls.initialized

    @classmethod
    def list_names(cls):
        return cls.counters.keys()

    @classmethod
    def dump(cls):
        d = {}
        for name in cls.counters:
            d[name] = cls.counters[name]._value
        return d

    def __init__(self, app_instance, name):
        # 引数を保存。app は使ってない。
        self.app = app_instance
        self.name = name
        # この値がNoneならマスターインスタンス
        # そうでなければサブトランザクション用のインスタンス
        self.parent = None
        # 保持するカウンター値
        self._value = Counter.base_value
        # トランザクションの書き込み対象のカウンター
        self._tmp_value = self._value

    # デバッグ・テスト用
    def who(self):
        print 'I am a master of "%s"' % self.name
        return [u'master', self.name]

    def create(self, mode, user_param=None):
        # mode, user_paramは使ってない、つうか、とりあえず無視
        return CounterRequester(self, self.name)

    def cleanup(self):
        print "Good bye from " + self.name

    def conflicts(self, param1, parm2):
        # 引数チェックは不要だが、念のため
        if not (param is None and param2 is None):
            # ユーザーパラメータはnullしかない
            raise Exception("bad args")
        return False # 同じ名前＆ユーザーパラメータであっても競合は起きない

    def start(self):
        # 自分を親にして、値をそのまま引き継がせる
        c = Counter(self, self._value, self.name)
        c._value = self._tmp_value
        c._tmp_value = self._tmp_value
        c.parent = self
        return c

    def commit(self):
        if self.parent is None:
            # マスターオブジェクトは自身の_tmp_valueを_valueにコピーする
            self._value = self._tmp_value
        else:
            # 自分の値を親にコピーする
            self.parent._tmp_value = self._tmp_value

    def cancel(self):
        # 自分の値を初期値に戻す
        self._tmp_value = self._value


class CounterRequester(object):

    def __init__(self, master, name):
        self.master = master
        self.name = name # もとはシステムパラメータ、デバッグ・テストに使う

    # デバッグ・テスト用
    def who(self):
        print 'I am a requester of "%s"' % self.name
        return [u'requester', self.name]

    # 固有のメソッド

    def value(self):
        # 現在の値
        return self.master._tmp_value

    def inc(self):
        self.master._tmp_value += Counter.step_value
        _print_value(self.master._tmp_value)

    def dec(self):
        self.master._tmp_value -= Counter.step_value
        _print_value(self.master._tmp_value)

    def reset(self):
        self.master._tmp_value = Counter.base_value
        _print_value(self.master._tmp_value)


