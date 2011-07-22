#coding: utf-8
from caty.session.memory import OnMemoryStorage
from caty.session.value import *
from caty.core.exception import InternalException
TYPE_MAPPING = {
    'memory': OnMemoryStorage,
}

def initialize(obj):
    u"""セッションモジュールの初期化。
    セッションモジュールは以下の要素により成り立っている。

    * SessionStorage
    * SessionInfo

    これらのうち SessionStorage だけが設定によって差し替え可能となる。
    デフォルトではメモリ内にセッション情報を保持する揮発性のセッションとなる。

    """
    t = obj['session']['type']
    storage_class = TYPE_MAPPING.get(t, None)
    if not storage_class:
        raise InternalException(u'Unknwon session type: $type', type=t)
    storage = storage_class(obj['session'], obj['key'])
    return storage


