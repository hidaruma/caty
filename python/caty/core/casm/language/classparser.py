#coding: utf-8
from topdown import *

from caty.core.casm.language.ast import ClassNode, ScalarNode, CommandURI, CommandNode, ClassRefNode
from caty.core.casm.language.schemaparser import schema, typedef, type_arg
from caty.core.casm.language.syntaxparser import syntax
from caty.core.casm.language.facilityparser import _entity
from caty.core.casm.language.commandparser import command, refer, xjson, CallPattern, CommandDecl, CommandURI
from caty.core.casm.language.constparser import const
from caty.core.casm.language.kindparser import kind
from caty.core.language.util import *

def catyclass(seq):
    return choice(classdef, signature)(seq)

def classdef(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'class')(seq)
    classname = name_token(seq)
    if option(u':=')(seq):
        ref = identifier_token_m(seq)
        S(u';')(seq)
        return AliasNode(classname, ref, u'class')
    type_args = seq.parse(option(type_arg, []))
    dom, codom = option(restriction, (ScalarNode(u'univ'), None))(seq)
    defined = True
    redifinable = False
    with strict():
        e = option(choice(S(u'='), S(u'?='), S(u'&=')), u'=')(seq)
        if option(S(u'{'))(seq):
            member = many([command, property, schema, const, _entity])(seq)
            S(u'}')(seq)
            ref = refers(seq)
            nohook(S(u';'))(seq)
            doc2 = postfix_docstring(seq)
            doc = concat_docstring(doc, doc2)
            return ClassNode(classname, member, dom, codom, ref, doc, annotations, type_args, e)
        else:
            name = identifier_token_a(seq)
            nohook(S(u';'))(seq)
            doc2 = postfix_docstring(seq)
            doc = concat_docstring(doc, doc2)
            return ClassRefNode(classname, name, dom, codom, CommandURI([(u'python', 'caty.core.command.DummyClass')]), doc, annotations, type_args)

def signature(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    keyword(u'signature')(seq)
    annotations.add(Annotation(u'__signature'))
    classname = name_token(seq)
    if option(u':=')(seq):
        ref = identifier_token_m(seq)
        S(u';')(seq)
        return AliasNode(classname, ref, u'class')
    type_args = seq.parse(option(type_arg, []))
    dom, codom = option(restriction, (ScalarNode(u'univ'), None))(seq)
    with strict():
        option(S(u'='))(seq)
        if option(S(u'{'))(seq):
            member = many([abs_command, abs_type, _entity])(seq)
            S(u'}')(seq)
            ref = refers(seq)
            nohook(S(u';'))(seq)
            doc2 = postfix_docstring(seq)
            doc = concat_docstring(doc, doc2)
            return ClassNode(classname, member, dom, codom, ref, doc, annotations, type_args)
        else:
            name = identifier_token_a(seq)
            nohook(S(u';'))(seq)
            doc2 = postfix_docstring(seq)
            doc = concat_docstring(doc, doc2)
            return ClassRefNode(classname, name, dom, codom, CommandURI([(u'python', 'caty.core.command.DummyClass')]), doc, annotations, type_args)

def abs_type(seq):
    type = schema(seq)
    if type.defined:
        raise ParseError(seq, u'Type can not defined in signature class')
    return type

def abs_command(seq):
    cmd = command(seq)
    if cmd.script_proxy or cmd.reference_to_implementation.defined:
        raise ParseError(u'Command can not defined in signature class')
    return cmd

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
        return CommandNode(pname, [CallPattern(None, None, CommandDecl((ScalarNode(u'void'), tp), [], []))], CommandURI([(u'python', 'caty.core.command.Dummy')], False), doc, annotations, [])


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

