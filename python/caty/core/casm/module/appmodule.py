#coding: utf-8
from caty.core.casm.module.basemodule import *

class AppModule(Module):
    def __init__(self, app, parent=None, is_root=False):
        Module.__init__(self, app)
        self.fs = app._schema_fs
        self.pcasm_cache = None
        self.parser_cache = None
        self.command_loader = CommandLoader(app._command_fs)
        self.parent = parent
        self.is_root= is_root
        self.is_builtin = False
        self._plugin.set_fs(app._command_fs)

    def _path_to_module(self, path):
        return path.strip('/').split(u'/')[-1].rsplit('.')[0]

    def compile(self):
        # アプリケーションルートのpublicモジュールかパッケージからのみ呼ばれる
        assert self.is_root == True or self.is_package == True
        for e in self.fs.DirectoryObject(self.package_root_path).read():
            if e.is_dir and '.' not in e.basename:
                self._compile_dir(e)
            else:
                self._compile_file(e)

    def _compile_file(self, e):
        if self.is_root and e.path == u'/public.casm':
            self.filepath = e.path
            self.application.i18n.write(u'[WARNING] public.casm is obsolete')
            self.application._system.deprecate_logger.warning(u'public.casm is obsolete: %s' % self.application.name)
            # self._compile(e.path)
        elif (e.path.endswith(u'.casm') 
                or e.path.endswith(u'.pcasm') 
                or e.path.endswith(u'.casm.lit')
                or e.path.endswith(u'.casm.frag')
                or e.path.endswith(u'.casm.frag.lit')):
            mod = self._get_module_class()(self._app, self)
            mod.filepath = e.path
            if e.path.endswith(u'.casm.lit') or e.path.endswith(u'.casm.frag.lit'):
                mod._literate = True
            if u'.casm.frag' in e.path:
                mod._fragment = True
            mod._name = unicode(self._path_to_module(e.basename))
            mod._compile(e.path)

            if self.has_module(mod.canonical_name):
                raise Exception(self.application.i18n.get(u'Module $name is already defined in $app', 
                                                          name=mod.canonical_name, 
                                                          app=self.get_module(mod.canonical_name)._app.name))
            self.sub_modules[mod.name] = mod
            mod.last_modified = e.last_modified
        elif e.path == u'/formats.xjson':
            o = self.fs.open(e.path)
            self._plugin.feed(o.read())

    def _compile_dir(self, e, pkg_class=None):
        if not pkg_class:
            pkg_class = Package
        mod = pkg_class(self._app, self)
        mod._name = unicode(self._path_to_module(e.basename.strip(u'/')))
        mod.package_root_path = e.path
        mod.compile()
        if self.has_package(mod.canonical_name):
            raise Exception(self.application.i18n.get(u'Package $name is already defined in $app', 
                                                      name=mod.name, 
                                                      app=self.get_package(mod.name)._app.name))
        with self.fs.open(join(e.path, mod.PACKAGE_FILE)) as pkg:
            if pkg.exists:
                c = pkg.read()
                try:
                    pkginfo = xjson.loads(c)
                except Exception as e:

                    raise Exception(self.application._system.i18n.get(u'Failed to parse JSON: $path\n$error', path=pkg.path, error=error_to_ustr(e)))
                mod.docstring = pkginfo.get('description', u'')
                mod.more_docstring = pkginfo.get('moreDescription', None)
                annotations = pkginfo.get('annotations', {})
                for k, v in annotations.items():
                    mod.annotations.add(Annotation(k, v))
                mod._manifest = pkginfo
        self.sub_packages[mod.name] = mod
        return mod

    def _get_module_class(self):
        return self.__class__

    def _compile(self, path, force=False):
        o = self.fs.open(path)
        if path.endswith('.pcasm'):
            d = to_decl_style(o)
            if self.pcasm_cache:
                io = self.pcasm_cache
            else:
                io = StringIO(d)
                io.path = o.path
                self.pcasm_cache = io
            res = self.parse_casm(io)
        elif path.endswith('.xcasm'):
            res = self.parse_casm(o, 'xcasm')
        else:
            if not self._literate:
                res = self.parse_casm(o, 'casm', self._fragment)
            else:
                res = self.parse_casm(o, 'lit', self._fragment)
        for t in res:
            if t.declare(self) == u'stop' and not force:
                break

    def parse_casm(self, fo, type='casm', fragment=False):
        try:
            if type == 'casm':
                self._show_msg(fo)
                self._app.cout.write(u'...')
                r = parse(fo.read(), fragment)
            elif type == 'xcasm':
                r = xcasm.parse(fo.read())
            elif type == 'lit':
                self._show_msg(fo)
                self._app.cout.write(u'...')
                r = parse_literate(fo.read(), fragment)
        except:
            self._app.cout.writeln(u'NG')
            raise
        else:
            self._app.cout.writeln(u'OK')
        return r

    def find(self, do):
        for e in do.read():
            if not e.is_dir:
                yield e
            else:
                for se in self.find(e):
                    yield se

    def _show_msg(self, fo, error=False):
        msg = self._app.i18n.get('Schema: $path', path=fo.path.strip('/'))
        self._app.cout.write(u'  * ' + msg)

    def to_name_tree(self):
        c = {}
        for k, v in self.schema_ns.items():
            if self.__in_core_or_global_schema(k):
                continue
            c[k] = {
                u'kind': u'i:type',
                u'id': unicode(str(id(v))),
                u'childNodes': {}
            }
        for k, v in self.command_ns.items():
            if self.__in_core_or_global_command(k):
                continue
            if '.' not in k:
                c[k] = {
                    u'kind': u'i:cmd',
                    u'id': unicode(str(id(v))),
                    u'childNodes': {}
                }
        for k, v in self.sub_modules.items():
            if v._type not in ('cara', 'cara.lit') and not self.__in_core_or_global_module(k):
                if '.' not in k:
                    c[k] = v.to_name_tree()
                else:
                    c[k] = {
                        u'kind': u'ns:pkg',
                        u'id': unicode(str(id(v))),
                        u'childNodes': {
                            k.rsplit('.', 1)[-1]: v.to_name_tree()
                        }
                    }
        return {
            u'kind': u'c:mod',
            u'id': unicode(str(id(self))),
            u'childNodes': c
        }

    def __in_core_or_global_schema(self, k):
        if self._core:
            if k in self._core.schema_ns:
                return True
        if self._global_module:
            if k in self._global_module.schema_ns:
                return True
        return False

    def __in_core_or_global_command(self, k):
        if self._core:
            if k in self._core.command_ns:
                return True
        if self._global_module:
            if k in self._global_module.command_ns:
                return True
        return False

    def __in_core_or_global_module(self, k):
        if self._core:
            if k in self._core.sub_modules:
                return True
        if self._global_module:
            if k in self._global_module.sub_modules:
                return True
        return False

class Package(AppModule):
    is_package = True
    PACKAGE_FILE = u'pkg-manifest.xjson'

    def __init__(self, *args, **kwds):
        AppModule.__init__(self, *args, **kwds)
        self.more_docstring = None
        self._manifest = {}

    def _get_module_class(self):
        return AppModule

