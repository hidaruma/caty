#coding: utf-8
from topdown import *

from caty.core.casm.language.ast import ClassNode, ScalarNode, CommandURI
from caty.core.casm.language.schemaparser import schema, typedef
from caty.core.casm.language.syntaxparser import syntax
from caty.core.casm.language.commandparser import command, refer
from caty.core.casm.language.constparser import const
from caty.core.casm.language.kindparser import kind
from caty.core.language.util import *

def catyclass(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'class')(seq)
    classname = name_token(seq)
    rest = option(restriction, ScalarNode(u'univ'))(seq)
    with strict():
        S(u'{')(seq)
        member = many([command])(seq)
        S(u'}')(seq)
        ref = refers(seq)
        S(u';')(seq)
        return ClassNode(classname, member, rest, ref, doc, annotations)

def restriction(seq):
    S('(')(seq)
    r = typedef(seq)
    S(')')(seq)
    return r

def refers(seq):
    try:
        return CommandURI(many1(refer)(seq))
    except:
        return CommandURI([(u'python', 'caty.core.command.DummyClass')])
