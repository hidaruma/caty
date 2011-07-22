#coding:utf-8
from caty.jsontools import raw_json as json
from caty.jsontools import CatyEncoder
from decimal import Decimal

def load(fo):
    u"""ファイル類似オブジェクトより JSON データをロードする。
    """
    return json.load(fo, parse_float=Decimal)

def loads(s):
    u"""文字列より JSON データをロードする。
    """
    return json.loads(s, parse_float=Decimal)

def dump(obj, fo, **kwds):
    return json.dump(obj, fo, cls=CatyEncoder, **kwds)

def dumps(obj, **kwds):
    return json.dumps(obj, cls=CatyEncoder, **kwds)



