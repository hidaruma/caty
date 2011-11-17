# coding: utf-8
from __future__ import with_statement
from __future__ import division
import caty
import caty.jsontools as json
from caty.jsontools import xjson
from caty.core.schema.base import JsonSchemaError
from caty.jsontools import *
from caty.core.command import Builtin, Internal, Filter
from caty.core.command.exception import *
from caty.core.exception import *
from caty.core.handler import AppDispatcher, RequestHandler
from caty.core.action.dispatcher import DispatchError
from caty.core.template import Template, PlainFile
from caty.core.facility import PEND
from caty.template.core.renderer import *
from caty.command import MafsMixin
import caty.core.runtimeobject as ro

import os
import sys
import traceback
import codecs
from optparse import Values
from StringIO import StringIO
from threading import RLock

from pbc import PbcObject, Contract
   
class Expand(Builtin, MafsMixin, PbcObject):
    
    __properties__ = ['path']

    def setup(self, opts, path):
        self.path, self.fs = self.parse_canonical_path(path)
        self.raw = opts.raw
        self.resolve = not bool(opts.no_script)
        self.mode = opts.mode
        PbcObject.__init__(self)

    def execute(self, input):
        return self._expand(input)

    def dup(self, path):
        if not path.startswith('include@') and not '@' in path:
            path = 'include@' + path
        from caty.core.command.param import Argument
        p = Expand([], [Argument(path)])
        p.pub = self.pub
        p.include = self.include
        p.env = self.env
        p.interpreter = self.interpreter
        p.schema = self.schema
        p._prepare()
        return p

    def _load_context(self, path, input):
        u"""path に対応した caty スクリプトファイルを実行する。
        """
        builder = self.interpreter
        assoc_path =[path+ '.icaty', path + '.caty']
        for p in assoc_path:
            if self.fs.open(p, 'rb').exists:
                content = self.fs.open(p).read()
                cmd = builder.build(content)
                return cmd(input)
        return None

    def subtemplate(self, path, input):
        sub = self.dup(path)
        sub.builder = self.interpreter
        return sub._expand(input)

    def exec_filter(self, name, argv):
        c = self.interpreter.make_filter(name, argv[1:])
        return c(argv[0])

    def _expand(self, input):
        path = self.path
        _f = self.fs.open(path)
        if not _f.exists:
            raise CatyException(
                'HTTP_404', 
                u'File does not exists: $path',
                path=path
                )
        if _f.is_dir:
            raise CatyException(
                'HTTP_400',
                u'Failed to read file: $path',
                path=path
            )
        if not self.env.exists('FILE_PATH'):
            self.env.put('FILE_PATH', path)
        assoc = False
        if self.raw:
            fo = self.fs.open(path)
            return fo.read()
        if self.resolve:
            assoc = True
        try:
            debug = self.env.get('DEBUG') if self.env.exists('DEBUG') else False
            template = Template(path, assoc, self.fs, self.schema, debug)
            template.set_include_callback(self.subtemplate)
            template.set_filter_executor(self.exec_filter)
            if assoc:
                o = self._load_context(path, input)
                if o != None:
                    input = o
            if self.mode:
                m = opts.mode
                if m == 'text':
                    template.renderer = TextRenderer()
                elif m == 'html':
                    pass # デフォルトの動作
            fo = self.fs.open(path)
            template.context = input
            template.context['_FILE_PATH'] = self.env.get('FILE_PATH')
            template.context['_APP_PATH'] = self.env.get('APP_PATH')
            template.context['_HOST_URL'] = self.env.get('HOST_URL')
            template.context['_CATY_VERSION'] = self.env.get('CATY_VERSION')
            encoding = fo.encoding if fo.encoding else self.env.get('APP_ENCODING')
            is_text = fo.is_text
            outfile = codecs.getwriter(encoding)(StringIO())
            template.write(outfile)
            outfile.seek(0)
            if is_text:
                return unicode(outfile.read(), encoding)
            else:
                return outfile.read()
        except PlainFile:
            self.raw = True
            return self._expand(input)

    if caty.DEBUG:
        def __invariant__(self):
            assert self.path != None
            assert self.fs != None

        def _not_property_changed(self, r, old, *args, **kwds):
            assert self.path == old.path

        execute = Contract(execute)
        execute.ensure += _not_property_changed

class Expand2(Expand):
    pass

class Response(Builtin):
    
    def setup(self, opts):
       self.ext = opts.ext
       self.content_type = opts.content_type
       self.encoding = opts.encoding
       self.status = opts.status if opts.status else 200

    def execute(self, input):
        if not self.encoding:
            encoding = self.env.get('APP_ENCODING')
        else:
            encoding = self.encoding
        if self.content_type:
            tp = self.content_type
            if self.encoding:
                tp += '; charset=%s' % encoding
        elif self.ext:
            tp = self.pub.get_type(self.ext)
            if self.pub.is_text_ext(self.ext):
                tp += '; charset=%s' % encoding
        else:
            tp = 'application/octet-stream'
        if isinstance(input, unicode):
            length = len(input.encode(encoding))
        else:
            length = len(input)
        return {
            'status': self.status,
            'encoding': encoding,
            'body': input,
            'header': {
                'content-type': unicode(tp),
                'content-length': length
            }
        }

class Print(Expand):
    u"""組み込みの print コマンド。
    """
    
    def execute(self, input):
        path = self.path
        v = self._expand(input)
        fo = self.fs.open(path)
        if fo.is_text:
            ctype = '%s; charset=%s' % (fo.content_type, fo.encoding)
        else:
            ctype = fo.content_type
        encoding = fo.encoding if fo.encoding else self.env.get('APP_ENCODING')
        if isinstance(v, unicode):
            length = len(v.encode(encoding))
        else:
            length = len(v)
        return {
            'status': 200,
            'body': v,
            'header': {
                'content-length': length,
                'content-type': unicode(ctype)
            },
            'encoding': encoding
        }

class RequestTool(Internal):
    def setup(self, opts, path, *params):
        self._path = path
        self._method = opts.method or 'GET'
        self._verb = opts.verb or ''
        self._fullpath = opts.fullpath
        self._sub_setup(opts, path, *params)

    def _sub_setup(self, opts, path, *params):
        pass

    def find_app_and_path(self):
        if self._fullpath:
            dispatcher = AppDispatcher(self._system)
            app = dispatcher.dispatch(self._path)
            return app, self._path
        else:
            n = self._facilities['env'].get('CATY_APP')['name']
            p = self._facilities['env'].get('CATY_APP')['path']
            app = self._system.get_app(n)
            path = self._path if p == '/' else join(p, self._path)
            return app, path

class Request(RequestTool):
    
    def _sub_setup(self, opts, path, params=''):
        self._opts = self._split_opts(params)
        if opts.verb:
            self._opts['_verb'] = opts.verb
        self._content_type = opts.content_type
        self._debug = opts.debug or self._system.debug

    def _split_opts(self, params):
        r = {}
        for i in params.split('&'):
            if '=' in i:
                k, v = i.split('=')
                r[k] = v
        return r

    def execute(self, input):
        if self._content_type:
            content_type = self._content_type
        else:
            if not input:
                content_type = u''
            elif isinstance(input, dict):
                content_type = 'application/x-www-form-urlencoded'
            elif isinstance(input, TaggedValue):
                content_type = 'application/json'
            else:
                content_type = 'application/octed-stream'
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, ['web'], self._system, {'CONTENT_TYPE': content_type})
        for k, v in f.items():
            v.merge_transaction(self._facilities[k])
        handler = RequestHandler(f['interpreter'], 
                                 f['env'],
                                 app)
                                 #app.pub, 
                                 #app.web_config, 
                                 #app.encoding)
        cmd = handler.make_cmd(path, self._opts, self._method, PEND)
        cmd.exec_cmd(input, self._debug)
        if cmd.succeed:
            for k, v in self._facilities.items():
                v.merge_transaction(f[k])
        return cmd.result

class SelectScript(RequestTool):
    def _sub_setup(self, opts, path, *params):
        self._no_check = not opts.check
        self._exception = opts.exception
    
    def execute(self):
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, ['web'], self._system, {'CONTENT_TYPE': 'application/json'})
        for k, v in f.items():
            v.merge_transaction(self._facilities[k])
        handler = RequestHandler(f['interpreter'], 
                                 f['env'],
                                 app)
        try:
            path, _ = handler._create_path_and_vpath(path)
            entry = handler._verb_dispatcher.get(handler._file, path, self._verb, self._method, self._no_check)
        except Exception, e:
            if self._exception: raise
            entry = None
        if entry:
            return entry.source
        return None

class SelectAction(RequestTool):
    def _sub_setup(self, opts, path, *params):
        self._no_check = not opts.check
        self._exception = opts.exception
    
    def execute(self):
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, ['web'], self._system, {'CONTENT_TYPE': 'application/json'})
        for k, v in f.items():
            v.merge_transaction(self._facilities[k])
        handler = RequestHandler(f['interpreter'], 
                                 f['env'],
                                 app)
        try:
            path, _ = handler._create_path_and_vpath(path)
            entry = handler._verb_dispatcher.get(handler._file, path, self._verb, self._method, self._no_check)
        except Exception, e:
            if self._exception: raise
            entry = None
        if entry:
            if not entry.name:
                self.i18n.write(u'Not defined at CatyResourceAction file.')
                return entry.source
            return entry.canonical_name
        return False

class TraceDispatch(RequestTool):
    def _sub_setup(self, opts, path, *params):
        self._no_check = not opts.check

    def execute(self):
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, ['web'], self._system, {'CONTENT_TYPE': 'application/json'})
        for k, v in f.items():
            v.merge_transaction(self._facilities[k])
        handler = RequestHandler(f['interpreter'], 
                                 f['env'],
                                 app)
        try:
            path, _ = handler._create_path_and_vpath(path)
            t = handler._verb_dispatcher._get_trace(handler._file, path, self._verb, self._method, self._no_check)
            if any(map(lambda x:bool(x), t)):
                return json.tagged(u'EXISTS', t)
            else:
                return json.tagged(u'FAILED', t)
        except Exception, e:
            return json.tagged(u'FAILED', [None])


from topdown import *
from caty.core.schema.base import TagSchema, UnionSchema
from caty.core.casm.language import schemaparser
from caty.core.language import util
import operator
class TypeCalculator(object):
    def set_schema(self, s):
        scm = self.parse(s)
        self.converter = scm

    def parse(self, s):
        return as_parser(self.parse_type).run(s, auto_remove_ws=True)

    def parse_type(self, seq):
        return chainl(self.term, self.op)(seq)

    def term(self, seq):
        return seq.parse([self.type, self.tag, self.group])
    
    def tag(self, seq):
        _ = seq.parse('@')
        n = seq.parse(self.tag_name)
        t = seq.parse(self.type_name)
        return TagSchema(n, self.schema[n])

    def group(self, seq):
        _ = seq.parse('(')
        d = seq.parse(self.parse_type)
        _ = seq.parse(')')
        return d

    def op(self, seq):
        o = seq.parse(['&', '|', '++'])
        if o == '&':
            return operator.and_
        elif o == '++':
            return operator.pow
        else:
            return operator.or_

    def name(self, seq):
        return util.name(seq)
    
    def type(self, seq):
        return self.schema[self.type_name(seq)]

    def type_name(self, seq):
        return schemaparser.typename(seq)

    def error_report(self, e):
        if hasattr(e, 'to_path'):
            x = e.to_path(self.i18n)
            r = {}
            for k, v in x.items():
                r[unicode(k)] = v['message'] if isinstance(v['message'], unicode) else unicode(str(v['message']))
            return tagged(u'NG', r)
        else:
            return tagged(u'NG', e.get_message(self.i18n))

class Translate(Builtin, TypeCalculator):
    
    def setup(self, schema_name):
        self.schema_name = schema_name
        self.set_schema(schema_name)

    def execute(self, input):
        try:
            t, v = split_tag(input)
            scm = self.converter
            if t == 'form' or t == 'object':
                if t == 'object':
                    self.i18n.write(u'Plain object type is deprecated. Use with @form tag instead')
                return tagged(u'OK', scm.convert(self._to_nested(v)))
            elif t == 'json':
                try:
                    n = scm.fill_default(v)
                    scm.validate(n)
                    return tagged(u'OK', n)
                except JsonSchemaError, e:
                    return self.error_report(e)
        except JsonSchemaError, e:
            return self.error_report(e)

    def _to_nested(self, input):
        d = {}
        for k, v in input.items():
            d['$.'+k] = v
        return path2obj(d) if d else d

class Validate(Builtin, TypeCalculator):
    
    def setup(self, opts, schema_name):
        self.pred = opts.pred
        self.schema_name = schema_name
        self.set_schema(schema_name)

    def execute(self, input):
        try:
            scm = self.converter
            scm.validate(input)
            if self.pred:
                return True
            else:
                return tagged(u'OK', input)
        except JsonSchemaError, e:
            if self.pred:
                return False
            return self.error_report(e)



class Void(Builtin):
    
    def execute(self, input):
        return None

class Version(Builtin):
    
    def execute(self):
        return self.env.get('CATY_VERSION')


class PassData(Builtin):
    
    
    def execute(self, input):
        return input

class Nth(Builtin):
    
    def setup(self, n):
        self.num = n

    def execute(self, input):
        n = self.num
        if n < 1:
            raise IndexError(n)
        x = json.untagged(input)[n - 1] # 1始まり
        return x

class Item(Builtin):
    
    def setup(self, n):
        self.num = n

    def execute(self, input):
        x = json.untagged(input)[self.num] # 0 はじまり
        return x

class GetPV(Builtin):
    
    def setup(self, key):
        self.key = key

    def execute(self, input):
        x = json.untagged(input)[self.key]
        return x

class FindPV(Builtin):
    
    def setup(self, key):
        self.key = key

    def execute(self, input):
        if self.key in input:
            return tagged(u'EXISTS', input[self.key])
        else:
            return tagged(u'NO', None)

class Equals(Builtin):
    
    def execute(self, input):
        if input[0] == input[1]:
            return tagged(u'Same', input[0])
        else:
            return tagged(u'Diff', input)

class Eval(Builtin):
    
    def execute(self, input):
        if isinstance(input, unicode):
            cmd = self.interpreter.build(input, transaction=PEND)
            return cmd(None)
        else:
            cmd = self.interpreter.build(input[0], transaction=PEND)
            return cmd(input[1])
        
from caty.command import MafsMixin
class Execute(Builtin, MafsMixin):
    
    def setup(self, path, *rest_args_and_opts):
        self.__path = path
        self.__opts, self.__args = self._parse_opts_and_args(rest_args_and_opts)

    def execute(self, input):
        cmd = self.interpreter.build(self.open(self.__path).read(), self.__opts, self.__args, transaction=PEND)
        return cmd(input)

    def _parse_opts_and_args(self, arg_list):
        opts = {}
        args = []
        key = None
        has_upcoming_value = False
        for a in arg_list:
            if a.startswith('--'):
                if '=' in a:
                    k, v = a.split('=', 1)
                    opts[k[2:]] = v.strip('"')
                    continue
                else:
                    key = k[2:]
                    continue
            if a == '=':
                has_upcoming_value = True
                continue
            if key and has_upcoming_value:
                opts[key] = a
                has_upcoming_value = False
                key = None
                continue
            if key:
                opts[key] = True
                key = None
            args.append(a)
        if args:
            args.insert(0, args[0])
        return opts, args

class DirIndex(Internal):
    
    def __init__(self, opt_list, arg_list, type_args=[]):
        Internal.__init__(self, None, arg_list, type_args)
        self.__opts = opt_list

    def setup(self, path, method):
        self.__path = path
        self.__method = method

    def execute(self, input):
        opts = self.__opts
        pub = self._facilities['pub']
        if not pub.opendir(self.__path).exists:
            raise FileNotFound(path=self.__path)
        _interpreter = self._facilities['interpreter']
        for e in ['html', 'xhtml', 'cgi', 'act', 'do', 'xml']:
            path = '%s/index.%s' % (self.__path, e)
            if pub.open(path).exists:
                break
        else:
            raise UnableToAccess(path=self.__path)
        proxy = self._app.verb_dispatcher.get(pub, path, u'', self.__method)
        if proxy.compiled:
            cmd = _interpreter._instantiate(proxy.instance, opts, [path, path])
        else:
            cmd = _interpreter.build(proxy.source, opts, [path, path])
        return cmd(input)

class GetTag(Builtin):
    
    def execute(self, input):
        return tag(input)

class Tagged(Builtin):
    
    def execute(self, input):
        return tagged(input[0], input[1])

class Untagged(Builtin):
    
    def setup(self, t=None):
        self.__tag = t

    def execute(self, input):
        if self.__tag is not None:
            t = tag(input)
            if t != self.__tag:
                raise Exception(ro.i18n.get(u'Not exptected tag: $expected!=$actual', expected=self.__tag ,actual=t))
        return untagged(input)

class ConsoleOut(Builtin):
    def setup(self, opts):
        self.nonl = opts.nonl
    
    def execute(self, input):
        self.stream.write(input)
        if (not self.nonl):
            self.stream.write('\n')

class ConsoleIn(Builtin):
    
    def execute(self):
        return xjson.loads(self.stream.read())

class DisplayApp(Builtin):
    
    def execute(self):
        return self.env.get('CATY_APP')

class DisplayApps(Builtin):
    
    def execute(self):
        return self.env.get('CATY_APPS')

class Home(Builtin):
    
    def setup(self, opts):
        self.full_path = opts.long

    def execute(self):
        if self.full_path:
            return self.env.get('CATY_HOME')
        else:
            return os.path.basename(self.env.get('CATY_HOME'))

class Location(Builtin):
    

    def execute(self):
        return self.env.get('CATY_HOME')

class Project(Builtin):
    

    def execute(self):
        return self.env.get('CATY_PROJECT')

class Manifest(Builtin):
    
    def execute(self):
        return self.env.get('APP_MANIFEST')

class ExecContext(Print):
    
    def setup(self, path):
        self.path = path
        self.resolve = True

    def execute(self, input):
        path = self.path
        if path.startswith('/'):
            self.fs = self.pub
        else:
            path = '/' + path
            self.fs = self.include
        template = Template(path, True, self.fs, self.schema)
        return self._load_context(path, input)

class Assoc(Internal):
    
    def setup(self, ext=None, verb=None):
        self.ext = ext
        self.verb = verb

    def execute(self):
        _assoc = self._app.verb_dispatcher
        assoc = {}
        for path, entries in _assoc._ftd._entries.items():
            e = {}
            for v, entry in entries._verbs.items():
                for m, ent in entry.items():
                    src = ent['command'].source
                    p = ent['parent']
                    if p:
                        k = v + '/' + m + '#exists-parent'
                    else:
                        k = v + '/' + m
                    e[k] = src
            assoc[path] = e
        if self.ext is None:
            return assoc
        else:
            if self.verb is None:
                return assoc.get(self.ext, {})
            return assoc.get(self.ext, {}).get(self.verb, None)

class ShowFileType(Builtin):
    
    def setup(self, ext=None):
        self.ext = ext

    def execute(self):
        if self.ext is None:
            return self.pub.all_types()
        else:
            return self.pub.all_types().get(self.ext, None)

class Param(Builtin):
    
    def setup(self, opts, arg=None):
        self.arg = arg
        self._default = opts.default

    def execute(self):
        if self.arg:
            return self.arg
        else:
            return self._default

from caty.util.path import join
class Redirect(Builtin):
    
    def setup(self, path=None):
        self.path = path

    def execute(self, input=None):
        if self.path is None:
            path = input
        else:
            path = self.path
        self.exit({
            'header': {
                'Location': unicode(join(self.env.get('HOST_URL'), path)),
            },
            'status': 302})

class LocalSchema(Builtin):
    
    def execute(self, input):
        self.schema.add_local(input)

class Binary(Builtin):
    

    def setup(self, format='base64'):
        self.format = format

    def execute(self, input):
        if self.format == 'raw':
            return str(input)
        elif self.format == 'base64':
            import base64
            return base64.b64decode(input)

class ListEnv(Builtin):
    

    def execute(self):
        r = {}
        for k, v in self.env.items():
            r[k] = v
        return r

class Properties(Builtin):
    

    def execute(self, input):
        return map(unicode, input.keys())


from types import *
import decimal

def _type_of(input):
    input_type = type(input)
    if input_type == NoneType:
        type_name = u'null'
    elif input_type == BooleanType:
        type_name = u'boolean'
    elif input_type == IntType or input_type == LongType or input_type == FloatType or \
            isinstance(input, decimal.Decimal):
        type_name = u'number'
    elif input_type == UnicodeType:
        type_name = u'string'
    elif input_type == ListType:
        type_name = u'array'
    elif input_type == DictType:
        type_name = u'object'
    elif isinstance(input, caty.jsontools.TaggedValue):
        type_name = u'tagged'
    elif input_type == StringType: # Uuuum by HIYAMA
        type_name = u'binary'
    else:
        type_name = u'unknown'
    return type_name

class TypeOf(Builtin):
    
    def execute(self, input):
        return _type_of(input)

class TypeIs(Builtin):
    
    def setup(self, type_name):
        self.type_name = type_name

    def execute(self, input):
        r = _type_of(input)
        return r == self.type_name

import caty
class Undef(Builtin):
    
    def execute(self):
        return caty.UNDEFINED

class Help(Builtin):
    def setup(self, opts, line=''):
        self.json = opts['json']
        if 'filter' in opts:
            self.query = opts['filter']
        else:
            self.query = None
        self.__exception = opts['exception']
        self.__mode = u'command'
        if opts['type'] and line:
            self.__type_name = line
            self.__mode = u'type'
        elif opts['command']:
            self.line = line
        elif opts['resource']:
            self.__resource_name = line
            self.__mode = u'resource'
        else:
            self.line = u''
        
    def execute(self):
        if self.__mode == u'type':
            return self._type_help()
        elif self.__mode == u'resource':
            return self._resources_help()
        else:
            return self._command_help()

    def _resources_help(self):
        line = self.__resource_name.strip()
        if line == '':
            return u''
        mode = 'usage'
        chunk = line.split(':')
        if len(chunk) == 1:
            if chunk[0] != '*':
                module = chunk[0]
                #mode = 'module_usage'
                return (u'引数エラー: %s' % line)
            else:
                return (u'引数エラー: %s' % line)
        else:
            if chunk[0] != '*':
                module = chunk[0]
                if chunk[0] == '':
                    return (u'引数エラー: %s' % line)
                elif chunk[1] == '*':
                    mode = 'resource_list'
                else:
                    resource = chunk[1]
                    if '.' in resource:
                        resource, action = resource.split('.', 1)
                        mode = 'action_usage'
                    else:
                        mode = 'resource_usage'
            else:
                mode = 'module_list'
        app = self.current_app
        rmc = app.resource_module_container
        if mode == 'module_list':
            mods = []
            for k, v in rmc._modules.items():
                mods.append((k+': ', v.docstring.split('\n')[0]))
            max_width = max(map(lambda x:len(x[0]), mods)) if mods else 0
            r = []
            for m in mods:
                r.append( (m[0].ljust(max_width + 1) + m[1]))
            return u'\n'.join(r)
        rm = rmc.get_module(module)
        if mode == 'resource_list':
            res = []
            for r in rm.resources:
                res.append((r.name, r.docstring.split('\n')[0] or u'undocumented'))
            max_width = max(map(lambda x:len(x[0]), res)) if res else 0
            r = []
            for m in res:
                r.append( (m[0].ljust(max_width + 1) + m[1]))
            return u'\n'.join(r)
        r = rm.get_resource(resource)
        if mode == 'resource_usage':
            return r.usage()
        else:
            a = r.get_action(action)
            return a.usage()


    def _type_help(self):
        line = self.__type_name.strip()
        if line == '':
            return u''
        module = 'public'
        mode = 'usage' # usage or list or module_usage oe list_modules
        chunk = line.split(':')
        if self.__exception:
            query = '__exception'
        else:
            query = None
        if len(chunk) == 1:
            if chunk[0] != '*':
                command = chunk[0]
                mode = 'usage'
            else:
                mode = 'list'
        elif len(chunk) == 2:
            if chunk[0] == '*':
                if chunk[1] == '':
                    mode = 'list_modules'
                else:
                    return (u'引数エラー: %s' % line)
            else:
                module = chunk[0]
                if chunk[1] == '':
                    return (u'引数エラー: %s' % line)
                elif chunk[1] == '*':
                    mode = 'list'
                else:
                    pass
        if mode == 'usage':
            try:
                return self._get_type()
            except KeyError:
                return (u'未知の型: %s' % self.__type_name)
        elif mode == 'list':
            r= []
            types = [(s.name, s.docstring) 
                     for s in self.schema._module.get_module(module).schema_ns.values()
                     if (not query) or (query in s.annotations)
                    ]
            types.sort(cmp=lambda x, y:cmp(x[0], y[0]))
            if types:
                max_width = max(map(lambda a:len(a[0]), types))
            else:
                max_width = 0
            r.append((u'モジュール: %s' % module))
            for c in types:
                if c[0] in caty.core.schema.types and module != 'public': continue
                r.append( (c[0].ljust(max_width + 1) + c[1]))
            return '\n'.join(r)
        elif mode == 'list_modules':
            r1 = []
            r2 = []
            for m in self.schema._module.get_modules():
                if m.application.name not in ('builtin', 'global'):
                    r2.append((m.application.name + ':' + m.name))
                else:
                    r1.append((m.name))
            r2.sort()
            r1.sort()
            r1.insert(0, (u'モジュール一覧'))
            return '\n'.join(r1+r2)
        else:
            return u''

    def _get_type(self):
        from caty.core.casm.cursor import TreeDumper
        from caty.core.schema import types
        t = self.__type_name.strip()
        if t in types:
            return u'基本型: ' + t
        st = self.schema._module.get_syntax_tree(t)
        td = TreeDumper()
        r = td.visit(st)
        return r

    def _command_help(self):
        interpreter = self.interpreter
        line = self.line.strip()
        if line == '':
            line = 'help'
        if line in ('change', 'reload', 'l', 'quit', 'ch', 'cd', 'server'):
            from caty.front.console import CatyShell
            h = getattr(CatyShell, 'do_%s' % line)
            return h.__doc__.strip()
        module = 'builtin'
        mode = 'usage' # usage or list or module_usage oe list_modules
        command = ''
        chunk = line.split(':')
        if len(chunk) == 1:
            if chunk[0] != '*':
                command = chunk[0]
                mode = 'usage'
            else:
                mode = 'list'
        elif len(chunk) == 2:
            if chunk[0] == '*':
                if chunk[1] == '':
                    mode = 'list_modules'
                else:
                    return (u'引数エラー: %s' % line)
            else:
                module = chunk[0]
                if chunk[1] == '':
                    return (u'引数エラー: %s' % line)
                elif chunk[1] == '*':
                    mode = 'list'
                else:
                    command = chunk[1]
        if mode == 'usage':
            if interpreter.has_command(module, command):
                return (interpreter.get_help(module, command))
            else:
                return (u'未知のコマンド: %s' % command)
        elif mode == 'list':
            r= []
            l = list(interpreter.get_commands(module))
            if self.query:
                query = 'filter'
            else:
                query = None
            commands = [(x.name, x.doc.splitlines()[0].strip()) 
                         for x in l
                         if not query or query in x.annotations]
            commands.sort(cmp=lambda x, y:cmp(x[0], y[0]))
            if commands:
                max_width = max(map(lambda a:len(a[0]), commands))
            else:
                max_width = 0
            r.append((u'モジュール: %s' % module))
            for c in commands:
                r.append( (c[0].ljust(max_width + 1) + c[1]))
            return '\n'.join(r)
        elif mode == 'list_modules':
            r1 = []
            r2 = []
            for m in interpreter.get_modules():
                if m.application.name not in ('builtin', 'global'):
                    r2.append((m.application.name + ':' + m.name))
                else:
                    r1.append((m.name))
            r2.sort()
            r1.sort()
            r1.insert(0, (u'モジュール一覧'))
            return '\n'.join(r1+r2)
        else:
            return u''

class MakeException(Builtin):
    def setup(self, name, msg):
        self.__name = name
        self.__msg = msg

    def execute(self):
        if not self.schema.has_schema(self.__name):
            raise throw_caty_exception('ExceptionNotFound', u'Exception $type is not defined', type=self.__name)
        else:
            return CatyException(self.__name, self.__msg).to_json()

class Throw(Builtin, TypeCalculator):
    def execute(self, input):
        if self._is_exception(input):
            t, v = json.split_tag(input)
            raise CatyException(t, v['message'])
        else:
            return input

    def _is_exception(self, input):
        etype = json.tag(input)
        if not self.schema.has_schema(etype):
            return False
        scm = self.schema[etype]
        if '__exception' not in scm.annotations:
            return False
        try:
            scm.validate(input)
        except Exception, e:
            print json.pp(self.error_report(e))
            return False
        return True

class ArrayToObject(Builtin):
    def execute(self, input):
        return dict(input)

class ObjectToArray(Builtin):
    def execute(self, input):
        return list(input.items())


import time
class Sleep(Builtin):
    def setup(self, millisec = 1000):
        self.millisec = millisec

    def execute(self):
        sec = self.millisec / 1000 # __future__ division
        time.sleep(sec)
        return None
