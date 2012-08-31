from caty.core.exception import *
from caty.core.command import Builtin
from caty.core.language import split_colon_dot_path

class FullPath(Builtin):
    def setup(self, opts):
        self.__as = opts['as']

    def execute(self, s):
        a, m, n = split_colon_dot_path(s, True)
        if n:
            if self.__as and self.__as[0] in (u'a', u'p', u'm'):
                throw_caty_exception(u'InvalidInput', u'$data', data=s)
            else:
                if self.__as in (u'cls', u'class'):
                    n += u'.'
        else:
            if self.__as and self.__as[0] in (u'c', u't'):
                throw_caty_exception(u'InvalidInput', u'$data', data=s)
        if a:
            a += '::'
        if m:
            if self.__as in (u'pkg', u'package'):
                m += u'.'
            else:
                m += ':'
        else:
            if self.__as and self.__as[0] in (u'p', u'm'):
                throw_caty_exception(u'InvalidInput', u'$data', data=s)
        return u''.join(filter(lambda x: x, [a, m, n]))
