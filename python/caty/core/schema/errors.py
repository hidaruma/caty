# coding: utf-8
from __future__ import absolute_import
from caty.util import *

# エラーメッセージの分類コード一覧
NOT_ERROR = -1          # エラーは発生していない
MISSING_PROPERTY = 0    # プロパティの不在 
UNEXPECTED_PROPERTY = 1 # 余分なプロパティの存在 
UNEXPECTED_VALUE = 2    # 型は合っているが値が違う
MISSING_ITEM = 3        # 項目の不在 
UNEXPECTED_ITEM = 4     # 余分な項目の存在 
BAD_TYPE = 5            # 型エラー 
BAD_TAG = 6             # タグのエラー 

class ErrorObj(object):
    u"""データ型の変換失敗時の情報を保持するオブジェクト。
    object 型に対する変換のエラーの詳細の報告に使う。
    主な使用箇所は Web ブラウザへの入力エラーの表示。
    """
    def __init__(self, is_error, orig, val, message):
        self.is_error = is_error # エラーかどうか。オブジェクトの検証などではエラーでないプロパティも含まれる
        self.orig = orig
        self.val = val
        self.error_message = message
        self._properties = {}
    
    def __setitem__(self, k, v):
        self._properties[k] = v

    def __getitem__(self, k):
        return self._properties[k]

    def values(self):
        return self._properties.values()

    def items(self):
        return self._properties.items()

    def keys(self):
        return self._properties.keys()

    def get_message(self, i18n, depth=0):
        m = [i18n.get(**self.error_message)]
        indent = ' ' * (depth * 4)
        for k, v in self.items():
            if isinstance(v, ErrorObj):
                m.append('%s%s: %s' % (indent, k, v.get_message(i18n, depth+1)))
            else:
                m.append('%s%s: %s' % (indent, k, error_to_ustr(v)))
        return '\n'.join(m)

    def update(self, o):
        self._properties.update(o)

    def to_dict(self, i18n=None):
        if i18n is None:
            from string import Template
            tmpl = Template(self.error_message['msg'])
            m = tmpl.safe_substitute(self.error_message)
        else:
            m = self.get_message(i18n)
        return {
            'isError': self.is_error,
            'orig': self.orig,
            'val': self.val,
            'message': m
        }

    def __repr__(self):
        return repr(self.to_dict())

    def __unicode__(self):
        if self.is_error:
            return self.to_dict()['message']
        else:
            return u''

class JsonSchemaError(ErrorObj, Exception):
    def __init__(self, msg, orig=u'', val=u''):
        Exception.__init__(self, msg)
        ErrorObj.__init__(self, True, orig, val, msg)

    def __repr__(self):
        return ErrorObj.__repr__(self)

class JsonSchemaErrorObject(JsonSchemaError):
    def __init__(self, *args, **kwds):
        JsonSchemaError.__init__(self, *args, **kwds)
        self.succ = {}

    def to_path(self, i18n):
        p = {}
        p.update(list(_flatten(self, i18n)))
        #s = obj2path(self.succ)
        #for k, v in s.items():
        #    p[k] = ErrorObj(False, to_unicode(v), to_unicode(v), u'').to_dict()
        return p

class JsonSchemaErrorList(JsonSchemaError):
    def __init__(self, msg, errors):
        JsonSchemaError.__init__(self, msg)
        self.errors = errors
        for i, v in enumerate(errors):
            self[i] = v

    def to_path(self, i18n):
        p = {}
        p.update(list(_flatten(self, i18n)))
        return p

    def __iter__(self):
        return iter(self.errors)

class JsonSchemaUnionError(JsonSchemaError):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2
        self.is_error = True

    def to_path(self, i18n):
        p = {}
        p.update(list(_flatten(self, i18n)))
        return p

    @property
    def error_message(self):
        return {
            u'msg': self.e1.error_message['msg'] + u' / ' + self.e2.error_message['msg']
        }

    @property
    def orig(self):
        return self.e1.orig

    @property
    def val(self):
        return self.e1.val


def _flatten(obj, i18n, parent='$'):
    if isinstance(obj, JsonSchemaErrorObject):
        for k, v in obj.items():
            for r in _flatten(v, i18n, parent + '.' + k):
                yield r
    elif isinstance(obj, JsonSchemaErrorList):
        for i, v in enumerate(iter(obj)):
            for r in _flatten(v, i18n, parent + '.' + str(i)):
                yield r
    elif isinstance(obj, JsonSchemaUnionError):
        t = []
        for e in _flatten(obj.e1, i18n, parent):
            t.append(e)
        for e in _flatten(obj.e2, i18n, parent):
            t.append(e)
        r = t[0]
        for _t in t[1:]:
            r['message'] = r['message'] + ' / ' + _t['message']
        yield r
    else:
        yield parent, obj.to_dict(i18n)

