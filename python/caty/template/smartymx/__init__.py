# coding: utf-8
from caty.template.core.template import Template
from caty.template.core.loader import BytecodeLoader, TextBytecodePersister
from caty.template.core.compiler import Compiler
from caty.template.core.io import ResourceIO
from caty.template.smartymx.parser import SmartyMXParser
from caty.template.builder import build_template
__all__ = ['SmartyTemplate', 'SmartyCompiler']
def SmartyTemplate(template):
    u"""Smarty-mx 用テンプレートエンジン。
    """
    compiler = SmartyMxCompiler()
    resource_io = ResourceIO()
    t = build_template(compiler, ResourceIO())
    t.set_template(template)
    return t

class SmartyMXCompiler(Compiler):
    def get_parser(self):
        return SmartyMXParser()

    def build_st(self, fo):
        return SmartyMXParser().run(fo.read())

