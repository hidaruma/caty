# coding: utf-8
from caty.core.language import *

def make_structured_doc(s):
    u"""ドキュメンテーション文字列を概要と本文に分ける。
    詳細はIssue#538を参照。
    """
    if not s:
        s = u'undocumented'
    l = s.split('\n', 1)
    r = {}
    if len(l) == 2:
        a, b = l
    else:
        a = s
        b = u''
    r['description'] = a
    if b:
        r['moreDescription'] = b
    return r
