# coding:utf-8
u"""テンプレートエンジンの構築を行うモジュール。
テンプレートエンジンを単体で動作させる場合に使うコンビニエンスな関数を提供する。
"""
from caty.template.core.template import Template
from caty.template.core.loader import BytecodeLoader, TextBytecodePersister

def build_template(compiler, resource_io):
    u"""Template オブジェクトの構築を行う。
    compiler と resource_io はそれぞれ ICompiler と AbstarctResourceIO と
    同一のインターフェースを持っている必要がある。
    """
    persister = TextBytecodePersister()
    bloader = BytecodeLoader(compiler, resource_io, persister)
    return Template(bloader)

