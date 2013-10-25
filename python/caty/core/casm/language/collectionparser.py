#coding:utf-8
u"""
"""
from caty import UNDEFINED
from topdown import *
from caty.core.casm.language.ast import *
from caty.core.casm.language.schemaparser import *
from caty.core.casm.language.classparser import *

def collection_decl(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword('collection')(seq)
    name = identifier_token(seq)
    with strict():
        keyword(u'of')(seq)
        coltype = typedef(seq)
        if option(keyword(u'identified'))(seq):
            keypath = CasmJSONPathSelectorParser()(seq)._to_str()
            keytype = option(col_key_type)(seq)
        else:
            keypath = u'$.id'
            keytype = None
        if option(keyword(u'with'))(seq):
            mixinclass = class_expression(seq)
        else:
            mixinclass = None
        if option(keyword(u'under'))(seq):
            dbname = name_token(seq)
        else:
            dbname = u'default-database'

        nohook(S(u';'))(seq)
        doc2 = postfix_docstring(seq)
        doc = concat_docstring(doc, doc2)
    return CollectionDeclNode(name, coltype, mixinclass, keypath, keytype, dbname, doc, annotations)

@try_
def col_key_type(seq):
    r = scalar(seq)
    if r.name in (u'with', u'under'):
        raise ParseFailed(seq, r.name)
    return r

