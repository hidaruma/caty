# coding: utf-8
from caty.template.core.template import Template
from caty.template.core.loader import BytecodeLoader, TextBytecodePersister
from caty.template.core.compiler import Compiler
from caty.template.core.io import ResourceIO
from caty.template.genshi.htmlverifier import convert
from caty.template.genshi.translator import GenshiTranslator
from caty.template.builder import build_template
import sys
__all__ =['GenshiTemplate', 'build_compiler']

def GenshiTemplate(template, encoding=sys.getdefaultencoding()):
    u"""スタンドアローンで動作する Gneshi 風テンプレートエンジンを作成する。
    """
    compiler = build_compiler()
    resource_io = ResourceIO()
    t = build_template(compiler, resource_io)
    return t

def build_compiler():
    u"""リソース IO やローダーまでは初期化せず、
    テンプレートのコンパイラまでを作成する。
    """
    compiler = None
    return compiler

