#coding:utf-8
from caty.core.exception import *
from caty.core.command import Builtin
from caty.core.language import split_colon_dot_path
mod_map = {
    u'application': u'app',
    u'module': u'mod',
    u'package': u'pkg',
    u'type': u'typ',
    u'command': u'cmd',
    u'class': u'cls'
}
class FullPath(Builtin):
    def setup(self, opts):
        self.__as = mod_map.get(opts['as'], opts['as'])

    def execute(self, s):
        a, m, n = split_colon_dot_path(s, self.__as)
        if n:
            if self.__as in (u'app', u'pkg', u'mod'):
                throw_caty_exception(u'InvalidInput', u'$data', data=s)
            else:
                if self.__as == u'cls' or s.endswith(u'.'):
                    n += u'.'
        else:
            if self.__as and self.__as in (u'cmd', u'typ'):
                throw_caty_exception(u'InvalidInput', u'$data', data=s)
        if a:
            a += '::'
        if m:
            if self.__as == u'pkg' or (':' not in s and s.endswith('.')):
                m += u'.'
            else:
                m += ':'
        else:
            if self.__as and self.__as in (u'pkg', u'mod'):
                throw_caty_exception(u'InvalidInput', u'$data', data=s)
        return u''.join(filter(lambda x: x, [a, m, n]))


class ListBackends(Builtin):
    def setup(self, arg=u'this'):
        self.app_name = arg

    def execute(self):
        if self.app_name == u'this':
            app = self.current_app
        else:
            system = self.current_app._system
            app = system.get_app(self.app_name)
        return app.backend_info.values()

