# coding: utf-8
from __future__ import absolute_import
from caty.util import *
import caty.core.runtimeobject as ro
import caty.jsontools as json

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
        if is_error:
            assert isinstance(message, dict), message
        self._properties = {}
    
    def __setitem__(self, k, v):
        self._properties[k] = v

    def __getitem__(self, k):
        try:
            return self._properties[k]
        except:
            print self, self._properties
            raise

    def values(self):
        return self._properties.values()

    def items(self):
        return self._properties.items()

    def keys(self):
        return self._properties.keys()

    def get_message(self, i18n, depth=0):
        if not self.is_error:
            return u''
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
            return self.to_dict(ro.i18n)['message']
        else:
            return u''

class JsonSchemaError(ErrorObj, Exception):
    def __init__(self, msg, orig=u'', val=u''):
        Exception.__init__(self, msg)
        ErrorObj.__init__(self, True, orig, val, msg)

    def to_path(self, i18n):
        return {u'$': self.to_dict(i18n)}

    def __repr__(self):
        return ErrorObj.__repr__(self)

    def error_report(self, i18n):
        from caty.jsontools import tagged
        def _message(v):
            if isinstance(v, list):
                msg = u' / '.join([_message(e) for e in v])
            else:
                msg = v['message'] if isinstance(v['message'], unicode) else unicode(str(v['message']))
            return msg
        x = normalize_errors(self).to_path(i18n)
        r = {}
        for k, v in x.items():
            msg = _message(v)
            r[unicode(k)] = msg
        prev = None
        for k in reversed(sorted(r.keys())):
            if prev and prev.startswith(k+'.'):
                del r[k]
            elif r[k] == u'':
                del r[k]
            else:
                prev = k
        return r 

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

    def __unicode__(self):
        o = self.to_path(ro.i18n)
        return json.pp(o)


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

    def __unicode__(self):
        o = self.to_path(ro.i18n)
        return json.pp(o)


class JsonSchemaUnionError(JsonSchemaError):
    def __init__(self, *args):
        self.errors = args
        self.is_error = True
    
    @property
    def e1(self):
        return self.errors[0]

    @property
    def e2(self):
        return self.errors[1]

    def to_path(self, i18n):
        p = {}
        p.update(list(_flatten(self, i18n)))
        return p

    def get_message(self, i18n, depth=0):
        return u' / '.join([e.get_message(i18n) for e in self.errors])

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
        from caty.util.collection import filled_zip
        r = {}
        for e in obj.errors:
            for k, v in _flatten(e, i18n, parent):
                if k not in r:
                    r[k] = []
                r[k].append(v)
        for k, v in r.items():
            yield k, v
    else:
        yield parent, obj.to_dict(i18n)

def normalize_errors(err):
    # スキーマエラー情報を標準化する。
    # * ユニオン型のエラーを展開し、もっとも深い所でエラーになったグループを取り出す。
    # * 上記をリストやオブジェクトの中にも再帰的に適用する。
    if isinstance(err, JsonSchemaUnionError):
        errors = map(normalize_errors, _flatten_union(err))
        return JsonSchemaUnionError(*_most_deep_group(errors))
    elif isinstance(err, JsonSchemaErrorObject):
        for k, v in err.items():
            err[k] = normalize_errors(v)
        return err
    elif isinstance(err, JsonSchemaErrorList):
        for i, e in enumerate(err):
            err[i] = normalize_errors(e)
        return err
    else:
        return err

def _flatten_union(err):
    if isinstance(err, JsonSchemaUnionError):
        e1 = err.e1
        e2 = err.e2
        for e in _flatten_union(e1):
            yield e
        for e in _flatten_union(e2):
            yield e
    else:
        yield err

def _most_deep_group(errors):
    map = {}
    for e in errors:
        depth = _error_depth(e)
        if depth not in map:
            map[depth] = []
        map[depth].append(e)
    return map[list(sorted(map.keys()))[-1]]

def _error_depth(e, depth=0):
    if isinstance(e, JsonSchemaErrorObject):
        depth_list = []
        for k, v in e.items():
            depth_list.append(_error_depth(v, depth+1))
        depth_list.sort()
        return depth_list[-1]
    elif isinstance(e, JsonSchemaErrorList):
        depth_list = []
        for v in e:
            depth_list.append(_error_depth(v, depth+1))
        depth_list.sort()
        return depth_list[-1]
    elif isinstance(e, JsonSchemaUnionError):
        depth_list = []
        for v in e.errors:
            depth_list.append(_error_depth(v, depth+1))
        depth_list.sort()
        return depth_list[-1]
    else:
        return depth
