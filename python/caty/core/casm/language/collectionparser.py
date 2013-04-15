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
            keytype = option(typedef)(seq)
        else:
            keypath = u'$._id'
            keytype = None
        S(u';')(seq)
    return CollectionDeclNode(name, coltype, keypath, keytype, doc, annotations)
