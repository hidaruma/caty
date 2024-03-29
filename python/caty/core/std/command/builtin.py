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
from caty.core.spectypes import reduce_undefined
from caty.core.handler import WebInputParser
from caty.core.spectypes import UNDEFINED, INDEF

import os
import sys
import traceback
import codecs
from optparse import Values
from StringIO import StringIO
from threading import RLock

class Expand(Builtin, MafsMixin):
    
    def setup(self, opts, path):
        self.path, self.fs = self.parse_canonical_path(path)
        self.raw = opts.get('raw', caty.UNDEFINED)
        self.resolve = not bool(opts.get('no-script', caty.UNDEFINED))
        self.mode = opts.get('mode', caty.UNDEFINED)

    def execute(self, input):
        return self._expand(input)

    def dup(self, path):
        if not path.startswith('include@') and not '@' in path:
            path = 'include@' + path
        from caty.core.command.param import Argument
        p = self.__class__([], [Argument(path)])
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
                u'HTTP_404', 
                u'File does not exists: $path',
                path=path
                )
        if _f.is_dir:
            raise CatyException(
                u'HTTP_400',
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
                m = self.mode
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
            template.context['FILE_PATH'] = self.env.get('FILE_PATH')
            if self.env.exists('PATH_INFO'):
                template.context['PATH_INFO'] = self.env.get('PATH_INFO')
            template.context['APP_PATH'] = self.env.get('APP_PATH')
            template.context['HOST_URL'] = self.env.get('HOST_URL')
            template.context['CATY_VERSION'] = self.env.get('CATY_VERSION')
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

class Expand2(Expand):
    pass


class Response(Builtin):
    
    def setup(self, opts):
       self.ext = opts.get('ext', caty.UNDEFINED)
       if self.ext and self.ext[0] != '.':
         self.ext = u'.' + self.ext
       self.content_type = opts.get('content-type', caty.UNDEFINED)
       self.encoding = opts.get('encoding', caty.UNDEFINED)
       self.status = opts.get('status', caty.UNDEFINED) 

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
        st = self.status if self.status else 200
        if isinstance(input, dict):
            r = {}
            r.update(input)
            if self.status:
                r['status'] = self.status
            if 'status' not in r:
                r['status'] = st
            if 'encoding' not in r:
                r['encoding'] = encoding
            if 'header' not in r:
                r['header'] = {}
            if self.content_type or self.ext:
                r['header']['content_type'] = tp
            input = u''
        else:
            if isinstance(input, unicode):
                length = len(input.encode(encoding))
            else:
                length = len(input)
            r = {
            'status': st,
            'encoding': encoding,
            'body': input,
            'header': {
                'content-type': unicode(tp),
                'content-length': length
            }
        }
        return r


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
        self._method = opts.get('method', caty.UNDEFINED) or 'GET'
        self._verb = opts.get('verb', caty.UNDEFINED) or ''
        self._fullpath = opts.get('fullpath', caty.UNDEFINED)
        self._sub_setup(opts, path, *params)

    def _sub_setup(self, opts, path, *params):
        pass

    def find_app_and_path(self):
        if self._fullpath:
            dispatcher = AppDispatcher(self._system)
            app = dispatcher.dispatch(self._path)
            return app, self._path
        else:
            n = self._facilities['env'].get('APPLICATION')['name']
            p = self._facilities['env'].get('APPLICATION')['path']
            app = self._system.get_app(n)
            path = self._path if p == '/' else join(p, self._path)
            return app, path


class Request(RequestTool):
    
    def _sub_setup(self, opts, path, params=''):
        self._opts = self._split_opts(params)
        if opts.get('verb', caty.UNDEFINED):
            self._opts['_verb'] = opts.get('verb', caty.UNDEFINED)
        self._content_type = opts.get('content_type', caty.UNDEFINED)
        self._debug = opts.get('debug', caty.UNDEFINED) or self._system.debug

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
                content_type = 'application/octet-stream'
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        mode = [u'web']
        if u'test' in self.env.get('RUN_MODE'):
            mode.append(u'test')
        app.init_env(f, caty.DEBUG, mode, self._system, {'CONTENT_TYPE': content_type})
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
        self._no_check = not opts.get('check', caty.UNDEFINED)
        self._exception = opts.get('exception', caty.UNDEFINED)
    
    def execute(self):
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, [u'web'], self._system, {'CONTENT_TYPE': 'application/json'})
        for k, v in f.items():
            v.merge_transaction(self._facilities[k])
        handler = RequestHandler(f['interpreter'], 
                                 f['env'],
                                 app)
        try:
            path, _ = handler._create_path_and_vpath(path)
            entry = handler._verb_dispatcher.get(handler._file, path, self._verb, self._method, self._no_check).resource_class_entry
        except Exception, e:
            if self._exception: raise
            entry = None
        if entry:
            return entry.source
        return None


class SelectAction(RequestTool):
    def _sub_setup(self, opts, path, *params):
        self._no_check = not opts.get('check', caty.UNDEFINED)
        self._exception = opts.get('exception', caty.UNDEFINED)
    
    def execute(self):
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, [u'web'], self._system, {'CONTENT_TYPE': 'application/json'})
        for k, v in f.items():
            v.merge_transaction(self._facilities[k])
        handler = RequestHandler(f['interpreter'], 
                                 f['env'],
                                 app)
        try:
            path, _ = handler._create_path_and_vpath(path)
            entry = handler._verb_dispatcher.get(handler._file, path, self._verb, self._method, self._no_check).resource_class_entry
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
        self._no_check = not opts.get('check', caty.UNDEFINED)

    def execute(self):
        app, path = self.find_app_and_path()
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, [u'web'], self._system, {'CONTENT_TYPE': 'application/json'})
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
    def set_schema(self, s, close=None):
        from caty.core.casm.language.ast import UnaryOpNode
        tn = self.schema.make_type_normalizer()
        scm = self.parse(s)
        if self.type_params and self.type_params[0]._schema:
            self.converter = tn.visit(self.type_params[0]._schema & scm)
        else:
            self.converter = scm
        if close:
            self.converter = tn.visit(UnaryOpNode(u'close', self.converter))
        if self.converter.type == u'never' and not self.converter.optional and not self.accept_never:
            raise Exception(self.i18n.get(u'Type representation is never: $typedef', typedef=s))

    def parse(self, s):
        from caty.core.casm.language.schemaparser import typedef
        from caty.core.casm.language.ast import ASTRoot
        from caty.core.schema.base import Annotations
        from topdown import as_parser
        if self.mod:
            app_name, mod_name, _ = split_colon_dot_path(self.mod, u'mod')
            if _:
                throw_caty_exception('BadArg', u'$arg', arg=self.mod)
            if app_name == 'this':
                app = self.current_app
            else:
                app = self.current_app._system.get_app(app_name)
            mod = app._schema_module.get_module(mod_name)
        else:
            mod = self.schema.schema_finder
        ast = ASTRoot(u'', [], as_parser(typedef).run(s, auto_remove_ws=True), Annotations([]), u'')
        sb = mod.make_schema_builder()
        sb._root_name = self.__class__.__name__.lower()
        rr = mod.make_reference_resolver()
        cd = mod.make_cycle_detecter()
        ta = mod.make_typevar_applier()
        tn = mod.make_type_normalizer()
        tn.safe = True
        sb._root_name = self.__class__.__name__.lower()
        t = ast.accept(sb)
        t = t.accept(rr)
        t = t.accept(cd)
        t = t.accept(ta)
        t = t.accept(tn).body
        return t

class Validate(Builtin, TypeCalculator):
    
    def setup(self, opts, schema_name=u'univ'):
        self.pred = opts.get('boolean', caty.UNDEFINED)
        self.mod = opts.get('mod')
        self.accept_never = opts['accept-never-type']
        self.schema_name = schema_name
        self.set_schema(schema_name, opts.get('close'))

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
            return tagged(u'NG', e.error_report(self.i18n))


class Void(Builtin):
    
    def execute(self, input):
        return None


class Version(Builtin):
    
    def execute(self):
        return self.env.get('CATY_VERSION')



class PassData(Builtin):
    
    def execute(self, input):
        return input


class Default(Builtin):

    def setup(self, value):
        self.value = value

    def execute(self, input):
        if input is caty.UNDEFINED:
            return self.value
        else:
            return input


class Nth(Builtin):
    
    def setup(self, opts, n):
        self.num = n
        self.safe = opts['safe']

    def execute(self, input):
        n = self.num
        d = json.untagged(input)
        if d is caty.UNDEFINED:
            if not self.safe:
                throw_caty_exception(u'Undefined', unicode(str(n)))
            else:
                return caty.UNDEFINED
        # d は配列
        if n < 1 or n > len(d):
            if not self.safe:
                throw_caty_exception(u'Undefined', unicode(str(n)))
            else:
                x = caty.UNDEFINED
        else:
            x = d[n - 1] # 1始まり
            if x == caty.UNDEFINED and not self.safe:
                throw_caty_exception(u'Undefined', unicode(str(n)))
        return x


class Item(Builtin):
    
    def setup(self, opts, n):
        self.num = n
        self.safe = opts['safe']

    def execute(self, input):
        n = self.num
        try:
            x = json.untagged(input)[self.num] # 0 はじまり
        except:
            if not self.safe:
                throw_caty_exception(u'Undefined', unicode(str(n)))
            else:
                x = caty.UNDEFINED
        if x is caty.UNDEFINED and not self.safe:
            throw_caty_exception(u'Undefined', unicode(str(n)))
        return x


class GetPV(Builtin):
    
    def setup(self, opts, key):
        self.key = key
        self.safe = opts['safe']

    def execute(self, input):
        try:
            x = json.untagged(input)[self.key]
        except:
            if not self.safe:
                throw_caty_exception(u'PropertyNotExist', self.key)
            else:
                x = caty.UNDEFINED
        if x is caty.UNDEFINED and not self.safe:
            throw_caty_exception(u'Undefined', self.key)
        return x


class FindPV(Builtin):
    
    def setup(self, key):
        self.key = key

    def execute(self, input):
        if self.key in input and input[self.key] is not caty.UNDEFINED:
            return tagged(u'EXISTS', input[self.key])
        else:
            return tagged(u'NO', None)


class Equals(Builtin):
    def setup(self, opts):
        self._boolean = opts['boolean']

    def execute(self, input):
        input = reduce_undefined(input)
        while len(input) < 2:
            input.append(caty.UNDEFINED)
        res = self.__eq(*input)
        if res == INDEF:
            if self._boolean:
                return INDEF
            else:
                return tagged(u'Indef', input)
        elif res:
            if self._boolean:
                return True
            else:
                return tagged(u'True', input)
        else:
            if self._boolean:
                return False
            else:
                return tagged(u'False', input)

    def __eq(self, a, b):
        a = reduce_undefined(a)
        b = reduce_undefined(b)
        return self.__rec_eq(a, b)

    def __rec_eq(self, a, b):
        if isinstance(a, dict):
            if not isinstance(b, dict):
                return False
            else:
                if a.keys()!= b.keys():
                    return False
                return all([self.__rec_eq(a[k], b[k]) for k in a.keys()])
        elif isinstance(a, (tuple, list)):
            if not isinstance(b, (tuple, list)):
                return False
            if len(a) != len(b):
                return False
            return all([self.__rec_eq(p[0], p[1]) for p in zip(a, b)])
        elif _type_of(a) == _type_of(b) == 'foreign':
            return INDEF
        else:
            if a == b:
                if (isinstance(a, bool) and not isinstance(b, bool)) or (isinstance(b, bool) and not isinstance(a, bool)):
                    return False
                if (isinstance(a, str) and not isinstance(b, str)) or (isinstance(b, str) and not isinstance(a, str)):
                    return False
                return True
            return False

from caty.util import normalize_tribool
class And(Builtin):
    def execute(self, input):
        return reduce(self._and, map(normalize_tribool, input), True)

    def _and(self, a, b):
        if a == True:
            if b == True:
                return True
            elif b == False:
                return False
            return INDEF
        elif a == False:
            return False
        else:
            if b == False:
                return False
            return INDEF

class Or(Builtin):
    def execute(self, input):
        return reduce(self._or, map(normalize_tribool, input), False if len(input) > 0 else True)

    def _or(self, a, b):
        if a == True:
            return True
        elif a == False:
            if b == True:
                return True
            elif b == False:
                return False
            else:
                return INDEF
        else:
            if b == True:
                return True
            return INDEF

class Not(Builtin):
    def execute(self, input):
        return _not(normalize_tribool(input))

def _not(input):  
    if input == True:
        return False
    elif input == False:
        return True
    else:
        return INDEF

class Implies(Or):
    def execute(self, input):
        a = _not(normalize_tribool(input[0]))
        return self._or(a, normalize_tribool(input[1]))

_b_map = {
    (True, True): True,
    (True, False): False,
    (True, INDEF): INDEF,
    (False, True): False,
    (False, False): True,
    (False, INDEF): INDEF,
    (INDEF, True): INDEF,
    (INDEF, False): INDEF,
    (INDEF, INDEF): INDEF,
}

class Equiv(Builtin):
    def execute(self, input):
        return _b_map[(normalize_tribool(input[0]), normalize_tribool(input[1]))]

class Eval(Builtin):
    
    def execute(self, input):
        if isinstance(input, unicode):
            cmd = self.interpreter.build(input, transaction=PEND)
            return cmd(None)
        else:
            cmd = self.interpreter.build(input[1], transaction=PEND)
            return cmd(input[0])
        

class DirIndex(Internal):
    
    def __init__(self, opt_list, arg_list, type_args=[], pos=(None, None), module=None):
        Internal.__init__(self, None, arg_list, type_args, pos, module)
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
        proxy = self._app.verb_dispatcher.get(pub, path, u'', self.__method).resource_class_entry
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
        return tagged(*input)


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
        self.nonl = opts.get('no-nl', caty.UNDEFINED)
    
    def execute(self, input):
        self.stream.write(input)
        if (not self.nonl):
            self.stream.write('\n')


class ConsoleIn(Builtin):
# self.stream は使ってない
    def setup(self, prompt=u''):
        self.prompt = prompt

    def execute(self):
        return unicode(raw_input(self.prompt))


class DisplayApp(Builtin):
    
    def execute(self):
        return self.env.get('APPLICATION')


class DisplayApps(Builtin):
    
    def execute(self):
        siteInfoList= []
        for n in self.current_app._system.app_names:
            s = self.current_app._system.get_app(n)
            siteInfoList.append({'group': s._group.name, 'description': s.description, 'name': s.name, 'path': unicode(s.web_path)})
        return siteInfoList


class Home(Builtin):
    
    def setup(self, opts):
        self.full_path = opts.get('long', caty.UNDEFINED)

    def execute(self):
        if self.full_path:
            return self.env.get('PROJECT')['location']
        else:
            return os.path.basename(self.env.get('PROJECT')['location'])


class Location(Builtin):

    def execute(self):
        return self.env.get('PROJECT')['location']


class Project(Builtin):

    def execute(self):
        return self.env.get('PROJECT')['name']


class Manifest(Builtin):
    def setup(self, app_name=None):
        self.__app_name = app_name

    def execute(self):
        if self.__app_name:
            return self.current_app._system.get_app(self.__app_name)._manifest
        return self.current_app._manifest

class PkgManifest(Builtin):
    def setup(self, pkg_name):
        self.__pkg_name = pkg_name

    def execute(self):
        if '::' in self.__pkg_name:
            app_name, pkg_name = self.__pkg_name.split('::', 1)
        else:
            app_name = None
            pkg_name = self.__pkg_name
        if app_name:
            app = self.current_app._system.get_app(app_name)
        else:
            app = self.current_app
        return app._schema_module.get_package(pkg_name)._manifest

class PrjManifest(Builtin):
    def execute(self):
        return self.current_app._system._global_config._raw_data

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
    
    def setup(self, opts=None, ext=None, verb=None):
        self.ext = ext
        self.verb = verb

    def execute(self):
        _assoc = self._app.verb_dispatcher
        assoc = {}
        for cls, path_matcher in _assoc._selectors[2]._entries.items():
            e = {}
            for path, verb_matcher in path_matcher._entries.items():
                for v, methods in verb_matcher._verbs.items():
                    for m, ent in methods.items():
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


from caty.util.path import join
class Redirect(Builtin):
    
    def setup(self, path=None):
        self.path = path

    def execute(self, input=None):
        if self.path is None:
            path = input
        else:
            path = self.path
        raise ContinuationSignal({
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
    def setup(self, opts):
        self.toplevel = opts['toplevel']

    def execute(self):
        if self.toplevel:
            from caty.env import Env
            app = self.current_app
            env = Env().create(u'uses')
            facilities = {'env': env}
            app.init_env(facilities, self.env['DEBUG'], self.env['RUN_MODE'], app._system)
        else:
            env = self.env
        r = {}
        for k, v in env.items():
            r[k] = v
        return r


class Properties(Builtin):
    
    def execute(self, input):
        return map(unicode, input.keys())


from types import *
import decimal

def _type_of(input):
    from caty.core.spectypes import UNDEFINED, INDEF
    if input is UNDEFINED:
        return u'undefined'
    if input is INDEF:
        return u'indef'
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
    elif isinstance(input, (caty.jsontools.TagOnly, caty.jsontools.TaggedValue)):
        type_name = u'tagged'
    elif input_type == StringType: # Uuuum by HIYAMA
        type_name = u'binary'
    else:
        type_name = u'foreign'
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


class Undef(Builtin):
    
    def execute(self):
        return caty.UNDEFINED


import itertools
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
            self.__line = line
        elif opts['resource']:
            self.__resource_name = line
            self.__mode = u'resource'
        elif opts['special-command']:
            self.__mode = u'special'
            self.__line = line
        elif opts['syntax']:
            self.__mode = u'syntax'
        else:
            self.__line = u''

    def execute(self):
        if self.__mode == u'type':
            return self._type_help()
        elif self.__mode == u'resource':
            return self._resources_help()
        elif self.__mode == u'special':
            return self._special_command_help()
        elif self.__mode == u'syntax':
            return self._syntax_help()
        else:
            return self._command_help()

    def _resources_help(self):
        from caty.core.language.util import make_structured_doc
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
                mods.append((k+': ', make_structured_doc(v.docstring).get('description', u'undocumented')))
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
        from caty.core.casm.language.ast import KindReference
        from caty.core.language.util import make_structured_doc
        line = self.__type_name.strip()
        if line == '':
            return u''
        module = ''
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
            if module:
                modules = [module]
            else:
                modules = [u'builtin', u'public']
            for module in modules:
                types = [(s.name, make_structured_doc(s.docstring).get('description', u'undocumented')) 
                         for s in self.schema.get_module(module).schema_ns.values()
                         if ((not query) or (query in s.annotations)) and not isinstance(s, KindReference)
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
            return u'\n'.join(r)
        elif mode == 'list_modules':
            r1 = []
            r2 = []
            for m in itertools.chain(self.schema.get_modules(), *[p.get_modules() for p in self.schema.iter_parents()]):
                if m.application.name != 'caty':
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
        st = self.schema.get_syntax_tree(t)
        td = TreeDumper()
        r = td.visit(st)
        return r

    def _get_command(self):
        from caty.core.command.usage import CommandUsage
        from caty.core.schema import types
        t = self.__line.strip()
        ct = self.schema.get_command(t)
        r = CommandUsage(ct).get_usage()
        return r

    def _command_help(self):
        from caty.core.language.util import make_structured_doc
        interpreter = self.interpreter
        line = self.__line.strip()
        if line == '':
            self.__line = u'help'
            line = u'help'
        module = ''
        mode = 'usage' # usage or list or module_usage oe list_modules
        command = ''
        chunk = line.split(':')
        cls = u''
        if len(chunk) == 1:
            if chunk[0] != '*' and not '.*' in chunk[0]:
                command = chunk[0]
                mode = 'usage'
            else:
                if chunk[0] != '*':
                    cls = chunk[0].split('.*')[0]
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
                elif '.*' in chunk[1]:
                    cls = chunk[1].split('.*', 1)[0]
                    module = module + '.' + cls
                    mode = 'list'
                else:
                    command = chunk[1]
        if mode == 'usage':
            try:
                return self._get_command()
            except KeyError:
                return (u'未知のコマンド: %s' % self.__type_name)
        elif mode == 'list':
            r= []
            if self.query:
                query = 'filter'
            else:
                query = None
            if module:
                modules = [module]
            else:
                modules = [u'builtin', u'public']
            for module in modules:
                if '.' not in module:
                    mod = self.schema.get_module(module)
                    if cls and mod.has_class(cls):
                        mod = mod.get_class(cls)
                else:
                    m, c = module.split('.')
                    mod = self.schema.get_module(m).get_class(c)
                commands = [(s.name, make_structured_doc(s.docstring).get('description', u'undocumented')) 
                         for s in mod.command_ns.values()
                         if (not query) or (query in s.annotations) and not s.name.startswith('__')
                        ]
                commands.sort(cmp=lambda x, y:cmp(x[0], y[0]))
                if commands:
                    max_width = max(map(lambda a:len(a[0]), commands))
                else:
                    max_width = 0
                r.append((u'モジュール: %s' % module))
                for c in commands:
                    r.append( (c[0].ljust(max_width + 1) + c[1]))
            return u'\n'.join(r)
        elif mode == 'list_modules':
            r1 = []
            r2 = []
            for m in itertools.chain(self.schema.get_modules(), *[p.get_modules() for p in self.schema.iter_parents()]):
                if m.application.name != 'caty':
                    r2.append((m.application.name + ':' + m.name))
                else:
                    r1.append((m.name))
            r2.sort()
            r1.sort()
            r1.insert(0, (u'モジュール一覧'))
            return u'\n'.join(r1+r2)
        else:
            return u''

    def _special_command_help(self):
        line = self.__line.strip()
        if line == u'':
            return self._command_help()

        from caty.front.console import CatyShell
        props = dir(CatyShell)
        cmd = 'do_%s' % line
        if line == '*':
            r = []
            for p in props:
                if p.startswith('do_') and p != u'do_help':
                    h = getattr(CatyShell, p)
                    doc =  h.__doc__ or u'undocumented'
                    r.append(u'%s: %s' % (p.split('_', 1)[1], doc.strip().split('\n')[0]))
            return u'\n'.join(r)
        for p in props:
            if cmd == p:
                h = getattr(CatyShell, cmd)
                doc =  h.__doc__ or u'undocumented'
                return doc.strip()
        else:
            return u'Unknown special command: %s' % line

    def _syntax_help(self):
        from caty.core.language.util import make_structured_doc
        syntax_list = [make_structured_doc(s.docstring).get('description', u'')
                 for s in self.schema.get_module(u'builtin').command_ns.values()
                 if s.name.startswith(u'__')]
        r = []
        for s in syntax_list:
            if s not in (u'', u'undocumented'):
                r.append(s)
        return u'\n'.join(r)

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
        etype, data = json.split_tag(input)
        scm = self.schema.get_type(u'Exception')
        try:
            scm.validate(input)
        except Exception, e:
            throw_caty_exception(u'InvalidThrow', etype, origin=input)
        if not self.schema.has_schema(etype) or u'__exception' not in self.schema.get_type(etype).annotations:
            throw_caty_exception(u'ExceptionNotFound', etype, origin=input)
        msg = data.pop('message')
        if 'class' in data:
            cls = data.pop('class')
        else:
            cls = None

        if 'id' in data:
            id = data.pop('id')
        else:
            id = None
        
        if 'class' in data:
            cls = data.pop('class')
        else:
            cls = None

        if 'stackTrace' in data:
            st = data.pop('stackTrace')
        else:
            st = None
        throw_caty_exception(etype, msg, cls, id, st, **data)


class ArrayToObject(Builtin):
    def setup(self, opts):
        self.multi = opts['multi']

    def execute(self, input):
        if self.multi:
            r = {}
            for k, v in input:
                if k not in r:
                    r[k] = []
                r[k].append(v)
            return r
        else:
            r = {}
            for k, v in filter(lambda x: x is not UNDEFINED, input):
                if k not in r:
                    r[k] = v
                else:
                    throw_caty_exception(u'BadInput', u'Duplicated key: $data', data=k)
            return r


class ObjectToArray(Builtin):
    def setup(self, opts):
        self.multi = opts['multi']

    def execute(self, input):
        if self.multi:
            r = []
            for k, v in input.items():
                for i in v:
                    r.append([k, i])
            return r
        else:
            return list(input.items())


import time
class Sleep(Builtin):
    def setup(self, millisec = 1000):
        self.millisec = millisec

    def execute(self, input):
        sec = self.millisec / 1000 # __future__ division
        time.sleep(sec)
        return input


class ToString(Builtin):
    def execute(self, input):
        from caty.jsontools import raw_json as json
        if isinstance(input, unicode):
            return input
        v = json.dumps(input, cls=PPEncoder, ensure_ascii=False)
        if isinstance(v, unicode):
            return v
        else:
            return unicode(str(v))


from caty import ForeignObject
class Foreign(Builtin):
    def execute(self):
        return ForeignObject()


class Never(Builtin):
    def execute(self):
        throw_caty_exception(u'Never', u'never detected')


class Signal(Builtin):
    def setup(self, opts):
        self.runaway = opts['runaway']

    def execute(self, data):
        if self.runaway and json.tag(data) != u'runaway':
            data = json.tagged(u'runaway', data)
        send_caty_signal(data)


class Fill(Builtin):
    def execute(self, data):
        return self.in_schema.fill_default(data)
        
class ErrorToString(Builtin):
    def execute(self, e):
        return self.i18n.get(e.value.get('message', u''), e.value)

import caty.jsontools.selector as selector
from caty.core.script.query import Fetcher
class Dereference(Internal):
    def execute(self, ref):
        val = Fetcher().fetch_addr(ref, self.current_app, self._facilities, False)
        ref = untagged(ref)
        if len(ref['a']) == 2:
            stm = selector.compile(ref['a'][1])
            rel = stm.select(val).next()
            return json.tagged(u'Relative', [val, rel])
        else:
            return json.tagged(u'Total', val)
    
from caty.jsontools.selector.parser import JSONPathSelectorParser
from caty.jsontools.selector.stm import Selector
class Follow(Dereference):
    def setup(self, opts, path):
        self.__path = path
        self.auto = opts['auto']
        self.safe = opts['safe']

    def execute(self, ref):
        val = self.deref(ref)
        stm = DerefJSONPathSelectorParser(self).run(self.__path)
        return stm.select(val).next()

    def deref(self, ref):
        val = Dereference.execute(self, ref)
        if val.tag == 'Total':
            val = json.untagged(val)
        else:
            val = json.untagged(val)[1]
        return val

class DerefJSONPathSelectorParser(JSONPathSelectorParser):
    def __init__(self, follow):
        JSONPathSelectorParser.__init__(self, empty_when_error = follow.safe)
        self.follow = follow

    def dot(self, seq):
        sep = choice(u'.', u'!')(seq)
        def _(a, b):
            if sep == u'!' or self.follow.auto:
                if not isinstance(a, DerefWrapper):
                    a = DerefWrapper(a, self.follow)
                if not isinstance(b, DerefWrapper):
                    b = DerefWrapper(b, self.follow)
            return a.chain(b)
        return _

    def namewildcard(self, seq):
        t = seq.parse('*')
        raise ParseError(seq, t)

    def itemwildcard(self, seq):
        t = seq.parse('#')
        raise ParseError(seq, t)

    def oldtag(self, seq):
        t = seq.parse('^')
        raise ParseError(seq, t)

    def tag(self, seq):
        t = seq.parse('tag()')
        raise ParseError(seq, t)

    def exp_tag(self, seq):
        t = seq.parse('exp-tag()')
        raise ParseError(seq, t)
 
    def length(self, seq):
        t = seq.parse('length()')
        raise ParseError(seq, t)

class DerefWrapper(Selector):
    def __init__(self, selector, follow):
        Selector.__init__(self)
        self.selector = selector
        self.follow = follow

    def run(self, obj):
        for r in self.selector.run(obj):
            if json.tag(r) == u'__r':
                yield self.follow.deref(r)
            else:
                yield r

    def _to_str(self):
        return u'deref(%s)' % self.selector._to_str()

class Dissoc(Builtin):
    def execute(self, data):
        t = json.tag(data)
        if t in set([u'except', u'signal', u'normal']):
            return data
        else:
            body = json.untagged(data)
            t = json.tag(body['value'])
            if t in set([u'except', u'signal']):
                return body[u'value']
            else:
                body[u'value'] = json.untagged(body[u'value'])
                return json.tagged(u'normal', json.tagged(u'__mutate', body))


class TypeName(Builtin):
    def execute(self):
        return self.type_params[0].canonical_name


