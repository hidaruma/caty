# coding: utf-8
__all__ = ['check_grant', 'simple_checker', 'null_checker', 'AuthoriToken', 'CREATE', 'READ', 'UPDATE', 'DELETE']
import os

CREATE = 0
READ = 1
UPDATE = 2
DELETE = 3

_OP_MAP = {
    CREATE: 'CREATE',
    READ: 'READ',
    UPDATE: 'UPDATE',
    DELETE: 'DELETE',
    }

class AuthoriToken(object):
    u"""認可トークンクラス。
    """
    def __init__(self, token_value):
        self.__token_value = token_value

    @property
    def value(self):
        return self.__token_value

def check_grant(verb, fmap):
    u"""権限チェック関数。
    以下のようにデコレータとして使うことで、権限チェックを行う。

    @check_grant(CREATE, fmap)
    def createFile(authori_token, path, metadata): ...

    fmap は CRUD 処理に対応した関数の辞書であり、型を書くと

    int: AuthoriToken -> str -> bool

    という物になっている。
    この fmap によりアクセスコントロールの実装を差し替えることができる。
    実際には simple_checker などのラッパー関数を使い、以下のような API とすることを推奨する。

    @simple_checker(CREATE)
    def createFile(authori_token, path, metadata): ...
    """
    def wrapper(f):
        def check(token, path, *args, **kwds):
            checker_func = fmap.get(verb, None)
            if not checker_func:
                raise Exception('Undefined operation: %s, %s' % (path, str(verb)))
            if checker_func(token, path):
                return f(token, path, *args, **kwds)
            else:
                raise Exception('Operation not allowed: %s, %s' % (path, _OP_MAP[verb]))
        return check
    return wrapper

def simple_checker(verb):
    u"""権限チェック関数。
    Caty での権限は読み込み権限と更新権限及びその両者の混合権限である。
    権限はユーザアカウントではなくコマンドに与えられ、
    コマンドはコマンド宣言の reads, updates, uses 句により権限を取得する。
    """

    reader = 'reader'
    updator = 'updator'
    dual = 'dual'

    def check_create(token, path):
        v = token.value
        if v == dual:
            return True
        if v == updator:
            return True
        else:
            return False

    def check_read(token, path):
        v = token.value
        if v == dual:
            return True
        elif v == reader:
            return True
        else:
            return False

    def check_delete(token, path):
        v = token.value
        if v == dual:
            return True
        if v == updator:
            return True
        else:
            return False

    def check_update(token, path):
        v = token.value
        if v == dual:
            return True
        if v == updator:
            return True
        else:
            return False

    fmap = {
        CREATE: check_create,
        READ: check_read,
        UPDATE: check_update,
        DELETE: check_delete,
    }

    return check_grant(verb, fmap)

def null_checker(verb):
    u"""まったく権限チェックを行わない。
    """
    fmap = {
        CREATE: lambda a, b: True,
        READ: lambda a, b: True,
        UPDATE: lambda a, b: True,
        DELETE: lambda a, b: True,
    }

    return check_grant(verb, fmap)

