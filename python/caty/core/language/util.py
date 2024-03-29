# coding: utf-8
from caty.core.language import *

def make_structured_doc(s):
    u"""ドキュメンテーション文字列を概要と本文に分ける。
    詳細はIssue#538を参照。
    """
    if not s:
        return {}
    l = s.strip(u' \r\n').split('\n', 1)
    r = {}
    if len(l) == 2:
        a, b = l
    else:
        a = l[0]
        b = u''
    if a:
        r['description'] = a
        if b:
            r['moreDescription'] = b
    return r

def path_string(seq):
    return Regex(u'/[^/ \t\r\n;]*/?')(seq)

@nohook
@option
def postfix_docstring(seq):
    if seq.eof:
        return
    skip_ws(seq)
    if not option(S(u'//*'))(seq):
        if seq.parser_hook:
            seq.parser_hook.hook(seq)
        return
    doc = []
    doc.append(until('\n')(seq).strip())
    option(S('\n'))(seq)
    while not seq.eof and option(S('//'))(seq):
        doc.append(until('\n')(seq).lstrip('*'))
        option(S('\n'))(seq)
        many(u' ')(seq)
    if seq.parser_hook:
        seq.parser_hook.hook(seq)
    return '\n'.join(filter(lambda x: x, map(lambda x: x.strip(), doc)))

def concat_docstring(a, b):
    if a:
        if b:
            return a + '\n' + b
        else:
            return a
    if b:
        return b
    return None

