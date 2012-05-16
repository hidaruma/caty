#coding: utf-8
from topdown import *

from caty.core.casm.language.ast import ClassNode
from caty.core.casm.language.schemaparser import schema, typedef
from caty.core.casm.language.syntaxparser import syntax
from caty.core.casm.language.commandparser import command
from caty.core.casm.language.constparser import const
from caty.core.casm.language.kindparser import kind
from caty.core.language.util import *

def catyclass(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'class')(seq)
    classname = name_token(seq)
    rest = option(restriction)(seq)
    with strict():
        S(u'{')(seq)
        member = many([try_(schema), try_(syntax), try_(command), try_(const), try_(kind)])(seq)
        S(u'};')(seq)
    return ClassNode(classname, member, doc, annotation)

def restriction(seq):
    S('(')
    r = typedef(seq)
    S(')')
    return r
