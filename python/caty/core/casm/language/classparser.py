#coding: utf-8
from topdown import *

from caty.core.casm.language.ast import ClassNode, ScalarNode, CommandURI, CommandNode, ClassRefNode, ClassBody, ClassIntersectionOperator, UseOperator, UnuseOperator, CloseOperator, ClassReference, OpenOperator
from caty.core.casm.language.schemaparser import schema, typedef, type_arg, scalar, type_var
from caty.core.casm.language.syntaxparser import syntax
from caty.core.casm.language.facilityparser import _entity
from caty.core.casm.language.commandparser import command, refer, xjson, CallPattern, CommandDecl, CommandURI
from caty.core.casm.language.constparser import const
from caty.core.casm.language.kindparser import kind
from caty.core.language.util import *

def catyclass(seq):
    return classdef(seq)

def classdef(seq):
    doc = option(docstring)(seq)
    annotations = seq.parse(annotation)
    tp = choice(keyword(u'class'), keyword(u'signature'))(seq)
    if tp == 'signature':
        annotations.add(Annotation(u'__signature'))
    classname = class_name_token(seq)
    if option(u':=')(seq):
        ref = identifier_token_m(seq)
        S(u';')(seq)
        return AliasNode(classname, ref, u'class')
    type_args = seq.parse(option(type_arg, []))
    dom, codom = option(restriction, (ScalarNode(u'univ'), None))(seq)
    if '+' not in classname or classname.endswith('+'):
        conform = option(conforms)(seq)
    elif '+' in classname:
        conform = ScalarNode(classname.split('+')[-1])
    with strict():
        e = option(choice(S(u'='), S(u'?='), S(u'&=')), u'=')(seq)
        if option(peek(clsref))(seq):
            name = identifier_token_a(seq)
            nohook(S(u';'))(seq)
            doc2 = postfix_docstring(seq)
            doc = concat_docstring(doc, doc2)
            return ClassRefNode(classname, name, dom, codom, doc, annotations, type_args)
        else:
            expression = class_expression(seq)
            nohook(S(u';'))(seq)
            doc2 = postfix_docstring(seq)
            doc = concat_docstring(doc, doc2)
            return ClassNode(classname, expression, dom, codom, conforms, doc, annotations, type_args, e)

def clsref(seq):
    identifier_token_a(seq)
    return S(u';')(seq)

def op(seq):
    o = seq.parse(S(u'&'))
    return ClassIntersectionOperator

@try_
def class_expression(seq):
    return chainl(choice(class_term, use, unuse, open,  close, class_definition, class_ref), op, allow_trailing_operator=True)(seq)

def class_definition(seq):
    S(u'{')(seq)
    member = many([command, property, schema, const, _entity])(seq)
    S(u'}')(seq)
    ref = refers(seq)
    return ClassBody(member, ref)

def class_term(seq):
    _ = seq.parse('(')
    d = seq.parse(class_expression)
    _ = seq.parse(')')
    return d

@try_
def class_ref(seq):
    name = name_token(seq)
    ta = option(type_var, [])(seq)
    return ClassReference(name, ta)

def use(seq):
    def _use_item(seq):
        option(choice(S(u'command'), S(u'type')))(seq)
        name = choice(name_token, S(u'*'))(seq)
        if name != '*' and option(keyword(u'as'))(seq):
            alias = name_token(seq)
        else:
            alias = None
        return name, alias
    keyword(u'use')(seq)
    _ = seq.parse('(')
    r = option(split(_use_item, u','), [])(seq)
    _ = seq.parse(')')
    body = class_expression(seq)
    return UseOperator(r, body)

def unuse(seq):
    def _unuse_item(seq):
        option(choice(S(u'command'), S(u'type')))(seq)
        name = choice(name_token, S(u'*'))(seq)
        return name
    keyword(u'unuse')(seq)
    _ = seq.parse('(')
    r = option(split(_unuse_item, u','), [])(seq)
    _ = seq.parse(')')
    body = class_expression(seq)
    return UnuseOperator(r, body)

def close(seq):
    keyword(u'close')(seq)
    body = class_expression(seq)
    return CloseOperator(body)

def open(seq):
    keyword(u'open')(seq)
    body = class_expression(seq)
    return OpenOperator(body)

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
        return CommandURI([(u'python', 'caty.core.command')])
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
        return CommandURI([(u'python', 'caty.core.command')])

def conforms(seq):
    keyword('conforms')(seq)
    return choice(signature_spec, signature_spec_list)(seq)

def signature_spec(seq):
    return scalar(seq)

@try_
def signature_spec_list(seq):
    S(u'[')(seq)
    r = split(signature_spec, ',')(seq)
    S(u']')(seq)
    names = set()
    for n in r:
        if n.name in r:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Signature name conflicted: $name', name=n.name)
        names.add(n.name)
    return r



