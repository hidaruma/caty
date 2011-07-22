# coding: utf-8
u"""caty shell におけるテンプレートオブジェクト。
caty shell では mafs をバックエンドに用いてファイルへのアクセスを行うため、
caty.template.core で提供されているファイルシステムベースの ResourceIO は使えない。
また、ファイルの shebang を見てコンパイラのディスパッチ及びインラインスクリプトの処理を行う必要がある。
そのため、このモジュールでは ResourceIO の mafs バックエンドと
コンパイラのディスパッチャ、そしてそれらをまとめる関数を提供する。
このモジュールを使用する前に、適切に caty.system モジュールが初期化されていなければならない。
"""

from caty.template.core.io import IResourceIO
from caty.template.builder import build_template
from caty.template import smarty
from caty.template import smartymx
from caty.template import genshi

class MafsResourceIO(IResourceIO):
    def __init__(self, fs):
        self.fs = fs

    def open(self, path, mode='rb'):
        return self.fs.open(path, mode)

    def last_modified(self, path):
        return self.fs.open(path, 'rb').last_modified

    def exists(self, path):
        try:
            self.fs.open(path, 'rb').last_modified
        except:
            return False
        else:
            return True

from caty.core.shebang import parse
from StringIO import StringIO
class CompilerAndPreprocessor(object):
    u"""コンパイルの事前処理クラス。
    caty-meta 及び caty-script（解釈するよう指定された場合）を処理し、
    実際にコンパイルを行うモジュールの選択とインラインスクリプトの外部ファイルへの書き出しを行う。
    """
    def __init__(self, io):
        self._compilers = {
            'smarty': smarty.SmartyCompiler(),
            'smarty-mx': smartymx.SmartyMXCompiler(),
            'genshi': genshi.build_compiler(),
            }
        self._io = io

    def compile(self, fo):
        meta, script, content = parse(fo.read(), True)
        inline_script_path = fo.canonical_name + '.icaty'
        inline_script = self._io.open(inline_script_path)
        if inline_script.exists and fo.last_modified > inline_script.last_modified:
            if script:
                inline_script.close()
                inline_script_path = fo.canonical_name + '.icaty'
                f = self._io.open(inline_script_path, 'wb')
                f.write(script)
                f.close()
            else:
                inline_script.delete()
                inline_script.close()
        else:
            if script:
                inline_script.close()
                inline_script_path = fo.canonical_name + '.icaty'
                f = self._io.open(inline_script_path, 'wb')
                f.write(script)
                f.close()
        syntax = meta.get('template', '')
        if syntax == '':
            raise PlainFile()
        compiler = self._compilers[syntax]
        return compiler.compile(StringIO(content))

class PlainFile(Exception): pass

from caty.template.core.loader import TextBytecodePersister, BytecodeLoader

from caty.template.core import template
def Template(path, assoc, fs, schema_module, allow_undef=False):
    io = MafsResourceIO(fs)
    compiler = CompilerAndPreprocessor(io)
    persister = TextBytecodePersister()
    bloader = BytecodeLoader(compiler, io, persister)
    t = template.Template(bloader, schema_module)
    t.set_template(path)
    t.allow_undef = allow_undef
    return t

