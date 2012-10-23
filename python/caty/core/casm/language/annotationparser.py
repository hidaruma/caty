from caty.core.casm.language.commandparser import *
from caty.core.casm.language.ast import AnnotationDecl

def annotation_decl(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'annotation')(seq)
    name = name_token(seq)
    S(u'=')(seq)
    type = typedef(seq)
    S(u';')(seq)
    return AnnotationDecl(name, type, doc, annotations)
