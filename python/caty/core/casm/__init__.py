#coding:utf-8
from caty.core.casm.module import IntegratedModule
from caty.core.command import Builtin, Internal, Syntax, Command
import types

def initialize(system, builtins, std_modules):
    builtin_schema = create_builtin_schema(builtins)
    std_schema = map(lambda m:(m, create_std_schema(m)), std_modules)
    module = IntegratedModule(system)
    module.compile(builtin_schema, None)
    for mod, schema in std_schema:
        try:
            module.compile(schema, mod)
        except:
            print mod
            raise
    return module

join = lambda f: lambda *args: u'\n'.join(f(*args))
tolist = lambda f: lambda *args: list(f(*args))

def filter_command(mod):
    for item in filter(lambda a: isinstance(a, types.TypeType), mod.__dict__.values()):
        if issubclass(item, Builtin) and (item != Builtin and item != Syntax and item != Internal):
            schema_string = u"%s" % (item.command_decl)
            yield schema_string

@join
@tolist
def create_builtin_schema(modules):
    u"""ビルトインモジュールのスキーマ定義の生成。
    builtin.py の他、Caty スクリプトの内部で使われるコマンドの宣言、
    Catyシステム全体に関わるスキーマの定義を行う。
    """
    yield 'module builtin;'
    yield modules[0].schema
    yield modules[1].schema
    for s in filter_command(modules[1]):
        yield s

@join
@tolist
def create_std_schema(module):
    yield u'module %s;' % module.name
    yield module.schema
    #for s in filter_command(module):
    #    yield s
