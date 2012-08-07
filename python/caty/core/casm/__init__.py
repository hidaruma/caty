#coding:utf-8
from caty.core.casm.module import IntegratedModule
from caty.core.command import Builtin, Internal, Syntax, Command
import os
import sys
import types

def initialize(system, interpreter_module):
    builtin_schema = create_builtin_schema(interpreter_module)
    std_modules = [u'authutil',
                   u'debug',
                   u'file',
                   u'filter',
                   u'fit',
                   u'gen',
                   u'http',
                   u'inspect',
                   u'json',
                   u'list',
                   u'logging',
                   u'os',
                   u'path',
                   u'set',
                   u'strg',
                   u'test',
                   u'template',
                   u'text',
                   u'user',
                   u'viva',
                   u'xjson',
    ]
    std_schema = map(lambda m:(m, create_std_schema(m)), std_modules)
    module = IntegratedModule(system)
    module.compile(builtin_schema, None)
    for name, schema in std_schema:
        try:
            module.compile(schema, name)
        except:
            print name
            raise
    module.resolve()
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
def create_builtin_schema(module):
    yield import_caty_system_schema('builtin')
    yield module.schema
    for s in filter_command(module):
        yield s


@join
@tolist
def create_std_schema(name):
    yield import_caty_system_schema(name)
    #for s in filter_command(module):
    #    yield s

def import_caty_system_schema(name):
    import caty
    if hasattr(caty, '__loader__'):
        loader = caty.__loader__
        if hasattr(loader, 'zipfile'):
            return unicode(loader.get_data(os.path.join(loader.prefix, 'caty/core/std/schema', (name+'.casm'))), 'utf-8')
    return unicode(
        open(os.path.join(os.path.dirname(sys.argv[0]), 'python/caty/core/std/schema', (name+'.casm'))).read(),
        'utf-8')


