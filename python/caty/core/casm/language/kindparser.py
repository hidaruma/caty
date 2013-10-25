from topdown import *
from caty.core.casm.language.schemaparser import *
from caty.core.language.util import *

def kind(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    seq.parse(keyword('kind'))
    name_of_kind = seq.parse(name_token)
    if name_of_kind in RESERVED:
        raise ParseFailed(seq, kind, '%s is reserved.' % name_of_kind)
    seq.parse('=')
    seq.parse(expr)
    nohook(S(u';'))(seq)
    doc2 = postfix_docstring(seq)
    doc = concat_docstring(doc, doc2)
    return KindReference(name_of_kind, annotations, doc)

def expr(seq):
    seq.parse(choice(subset))

def subset(seq):
    seq.parse(choice(keyword('lower', 'upper')))
    seq.parse(typedef)

