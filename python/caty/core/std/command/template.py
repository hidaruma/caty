from caty.core.command import Builtin, Internal, Filter
from caty.core.exception import *
from caty.core.shebang import parse
from caty.template import compilers
from caty.template.core.st import Template, String
from StringIO import StringIO
import codecs

class TemplateObject(object):
    def __init__(self, object_code, script):
        self.object_code = object_code
        self.script = script

class Compile(Builtin):
    def execute(self, src):
        meta, script, content = parse(src, True)
        syntax = meta.get('template', '')
        if syntax == '':
            return TemplateObject([Template(String(src))])
        if syntax not in compilers:
            throw_caty_exception('TemplateCompileError', u'UnknownTemplateType: $syntax', syntax=syntax)
        compiler = compilers[syntax]
        return TemplateObject(compiler.compile(StringIO(content)), script)
    
from caty.command import MafsMixin
class Expand(Builtin, MafsMixin):

    def execute(self, input):
        return self._expand(input)

    def dup(self):
        p = Expand([], [])
        p.pub = self.pub
        p.include = self.include
        p.env = self.env
        p.interpreter = self.interpreter
        p.schema = self.schema
        p._prepare()
        return p

    def subtemplate(self, path, input):
        sub = self.dup()
        sub.builder = self.interpreter
        cmpl = Compile([], [])
        tpl = cmpl.execute(self.open(path).read())
        return sub._expand([tpl, input])

    def exec_filter(self, name, argv):
        c = self.interpreter.make_filter(name, argv[1:])
        return c(argv[0])

    def _expand(self, input):
        from caty.template.core.loader import TextBytecodePersister, BytecodeLoader
        from caty.template.core import template
        from caty.core.template import MafsResourceIO, CompilerAndPreprocessor
        tpl, context = input
        io = MafsResourceIO(self.include)
        compiler = CompilerAndPreprocessor(io)
        persister = TextBytecodePersister()
        bloader = BytecodeLoader(compiler, io, persister)
        t = template.Template(bloader, self.schema)
        t.code = tpl.object_code
        t.allow_undef = True
        t.set_include_callback(self.subtemplate)
        t.set_filter_executor(self.exec_filter)
        if tpl.script:
            cmd = self.interpreter.build(tpl.script)
            context = cmd(context)
        t.context = context
        t.context['_FILE_PATH'] = self.env.get('FILE_PATH')
        t.context['_APP_PATH'] = self.env.get('APP_PATH')
        t.context['_HOST_URL'] = self.env.get('HOST_URL')
        t.context['_CATY_VERSION'] = self.env.get('CATY_VERSION')
        t.context['FILE_PATH'] = self.env.get('FILE_PATH')
        if self.env.exists('PATH_INFO'):
            t.context['PATH_INFO'] = self.env.get('PATH_INFO')
        t.context['APP_PATH'] = self.env.get('APP_PATH')
        t.context['HOST_URL'] = self.env.get('HOST_URL')
        t.context['CATY_VERSION'] = self.env.get('CATY_VERSION')
        encoding = self.env.get('APP_ENCODING')
        outfile = codecs.getwriter(encoding)(StringIO())
        t.write(outfile)
        outfile.seek(0)
        return unicode(outfile.read(), encoding)

