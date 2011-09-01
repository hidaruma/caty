#coding:utf-8
from caty.core.schema.base import Annotations
from caty.core.exception import throw_caty_exception
from caty.jsontools import prettyprint
from caty.util import indent_lines, justify_messages
ABSOLUTE = 0
RELATIVE = 1
DEFAULT = 2

class ResourceClass(object):
    def __init__(self, url_pattern, actions, filetype, module_name, resource_name, docstring=u'Undocumented', annotations=Annotations([])):
        self.url_pattern = url_pattern
        self.url_patterns = self._split_pattern(iter(url_pattern))
        self.entries = actions
        self.name = resource_name
        self.module = module_name
        self.docstring = docstring
        self.annotations = annotations
        self.filetypes = {}
        if filetype:
            for p in self.url_patterns:
                self.filetypes[self._extract_ext(p)] = filetype
        if url_pattern.startswith('/'):
            self.type = ABSOLUTE
        else:
            self.type = RELATIVE
        for i, e in self.entries.items():
            e.annotations += self.annotations
            e.resource_name = resource_name
            e.module_name = module_name

    def _extract_ext(self, pattern):
        e = pattern.split('.').pop(-1)
        if e.endswith('/'):
            throw_caty_exception(u'CARA_PARSE_ERROR',
                                 u'Path pattern for filetype must be extension, but directory found: module=$mod, resource=$res',
                                 mod=self.module, res=self.name)
        return '.' + e

    def _split_pattern(self, seq):
        r = []
        buf_list = [[]]
        for c in seq:
            if c == '|':
                for b in buf_list:
                    if b:
                        r.append(''.join(b))
                buf_list = [[]]
            elif c == '(':
                sub = self._split_pattern(seq)
                buf_list[0].append(sub.pop(0))
                for s in sub:
                    buf_list.append([])
                    buf_list[-1].extend(buf_list[0][:-1])
                    buf_list[-1].append(s)
            elif c == ')':
                break
            else:
                for b in buf_list:
                    b.append(c)

        for b in buf_list:
            if b:
                r.append(''.join(b))
        return r

    def usage(self):
        buff = []
        buff.append((u'リソース名: ', self.name+'\n'))
        buff.append((u'URLパターン: ', self.url_pattern+'\n'))
        if self.entries:
            buff.append((u'アクション一覧: ', ''))
        m = justify_messages(buff)
        for inv, e in self.entries.items():
            m += ('\n' + e.usage(indent=1) + '\n')
        return self.docstring.strip() + '\n\n' + m

    def get_action(self, name):
        for inv, e in self.entries.items():
            if e.name == name:
                return e
        throw_caty_exception(
            u'ActionNotFound',
            u'$actionName is not defined in $moduleName:$resourceName',
            actionName=aname,
            moduleName=self.name
        )

class DefaultResource(ResourceClass):
    def __init__(self, url_pattern, actions, module_name, resource_name, docstring=u'Undocumented', annotations=Annotations([])):
        ResourceClass.__init__(self, url_pattern, actions, {}, module_name, resource_name, docstring, annotations)
        self.type = DEFAULT

