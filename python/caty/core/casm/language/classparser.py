#coding: utf-8
from topdown import *

from caty.core.casm.language.ast import ClassNode, ScalarNode, CommandURI, CommandNode
from caty.core.casm.language.schemaparser import schema, typedef, type_arg
from caty.core.casm.language.syntaxparser import syntax
from caty.core.casm.language.commandparser import command, refer, xjson, CallPattern, CommandDecl, CommandURI
from caty.core.casm.language.constparser import const
from caty.core.casm.language.kindparser import kind
from caty.core.language.util import *

def catyclass(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'class')(seq)
    classname = name_token(seq)
    type_args = seq.parse(option(type_arg, []))
    dom, codom = option(restriction, (ScalarNode(u'univ'), None))(seq)
    with strict():
        S(u'{')(seq)
        member = many([command, property])(seq)
        S(u'}')(seq)
        ref = refers(seq)
        S(u';')(seq)
        return ClassNode(classname, member, dom, codom, ref, doc, annotations, type_args)

def restriction(seq):
    S('(')(seq)
    dom = option(typedef, ScalarNode(u'univ'))(seq)
    codom = None
    if option(S(u'->'))(seq):
       codom = option(typedef, ScalarNode(u'univ'))(seq)
    S(')')(seq)
    return dom, codom

def property(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'property')(seq)
    with strict():
        pname = name_token(seq)
        S('::')(seq)
        tp = typedef(seq)
        if option(S('='))(seq):
            val = seq.parse(xjson.parsers)
            annotations.add(Annotation(u'__init__', val))
        S(u';')(seq)
        annotations.add(Annotation(u'__property__'))
        annotations.add(Annotation(u'bind'))
        return CommandNode(pname, [CallPattern(None, None, CommandDecl((ScalarNode(u'void'), tp), [], []))], CommandURI([(u'python', 'caty.core.command.Dummy')]), doc, annotations, [])


def refers(seq):
    try:
        return CommandURI(many1(refer)(seq))
    except:
        return CommandURI([(u'python', 'caty.core.command.DummyClass')])

    S(')')(seq)
    return r

def property(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'property')(seq)
    with strict():
        pname = name_token(seq)
        S('::')(seq)
        tp = typedef(seq)
        if option(S('='))(seq):
            val = seq.parse(xjson.parsers)
            annotations.add(Annotation(u'__init__', val))
        S(u';')(seq)
        annotations.add(Annotation(u'__property__'))
        annotations.add(Annotation(u'bind'))
        return CommandNode(pname, [CallPattern(None, None, CommandDecl((ScalarNode(u'void'), tp), [], []))], CommandURI([(u'python', 'caty.core.command.Dummy')]), doc, annotations, [])


def refers(seq):
    try:
        return CommandURI(many1(refer)(seq))
    except:
        return CommandURI([(u'python', 'caty.core.command.DummyClass')])

