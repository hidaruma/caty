from caty.core.casm.language.commandparser import *
from caty.core.casm.language.ast import AnnotationDecl

def annotation_decl(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'annotation')(seq)
    name = name_token(seq)
    S(u'::')(seq)
    type = typedef(seq)
    nohook(S(u';'))(seq)
    doc2 = postfix_docstring(seq)
    doc = concat_docstring(doc, doc2)
    return AnnotationDecl(name, type, doc, annotations)
