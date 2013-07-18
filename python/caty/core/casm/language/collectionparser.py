#coding:utf-8
u"""
"""
from caty import UNDEFINED
from topdown import *
from caty.core.casm.language.ast import *
from caty.core.casm.language.schemaparser import *

def collection_decl(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword('collection')(seq)
    name = identifier_token(seq)
    with strict():
        keyword(u'of')(seq)
        coltype = typedef(seq)
        if option(keyword(u'identified'))(seq):
            keypath = CasmJSONPathSelectorParser()(seq)
            keytype = option(col_key_type)(seq)
        else:
            keypath = u'$.id'
            keytype = None
        if option(keyword(u'within'))(seq):
            dbname = name_token(seq)
        else:
            dbname = u'default-database'
        nohook(S(u';'))(seq)
        doc2 = postfix_docstring(seq)
        doc = concat_docstring(doc, doc2)
    return CollectionDeclNode(name, coltype, keypath, keytype, dbname, doc, annotations)

@try_
def col_key_type(seq):
    r = scalar(seq)
    if r.name == u'within':
        raise ParseFailed(seq, u'within')
    return r

