#coding:utf-8
from topdown import *
from caty.core.script.parser import ScriptParser
from caty.core.casm.language.casmparser import module_decl
from caty.core.casm.language.schemaparser import object_, typedef
from caty.core.casm.language.util import docstring, annotation
from caty.jsontools.xjson import obj
from caty.core.action.resource import ResourceClass
from caty.core.action.module import ResourceModule
from caty.core.action.entry import ResourceActionEntry, ActionProfile
from caty.core.schema.base import Annotations
from caty.util import bind2nd
from caty.core.exception import throw_caty_exception

class ResourceActionDescriptorParser(Parser):
    def __init__(self, module_name, facility):
        self._script_parser = ScriptParser(facility)
        self._module_name = module_name

    def __call__(self, seq):
        mn = module_decl(seq, 'cara')
        name = mn.name
        ds = mn.docstring
        if name != self._module_name:
            raise ParseFailed(seq, self, u'module name mismatched: %s' % name)
        r = ResourceModule(name, ds)
        classes = seq.parse(many(self.resourceclass))
        if not seq.eof:
            raise ParseError(seq, self)
        for c in classes:
            for a in r:
                if a.name == c.name:
                    throw_caty_exception(
                        u'CARA_PARSE_ERROR',
                        u'Duplicated resource name: $name module: $module', 
                        name=c.name, module=name)
            r.append(c)
        return r

    def resourceclass(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        seq.parse(keyword('resource'))
        try:
            rcname = name(seq)
            url_pattern = self.url_pattern(seq)
            seq.parse('{')
            block = seq.parse(ActionBlock(rcname, self._script_parser, self._module_name))
            actions = block.actions
            filetype = block.filetype
            seq.parse('}')
            seq.parse(';')
            return ResourceClass(url_pattern, actions, filetype, self._module_name, rcname, ds, ann)
        except ParseFailed, e:
            raise ParseError(e.cs, e.cause, e._message)

    def url_pattern(self, seq):
        seq.parse('(')
        patterns = seq.parse(split(string, '|'))
        seq.parse(')')
        return u'|'.join(patterns)


class ActionBlock(Parser):
    def __init__(self, rcname, script_parser, module_name):
        self.rcname = rcname
        self.actions = {}
        self.filetype = {}
        self.names = set()
        self._script_parser = script_parser
        self._module_name = module_name

    def __call__(self, seq):
        option(self.filetype_)(seq)
        many(self.action)(seq)
        return self

    def filetype_(self, seq):
        seq.parse('filetype')
        o = seq.parse(obj)
        self.filetype['contentType'] = o['contentType']
        self.filetype['isText'] = o['isText']
        seq.parse(';')

    def action(self, seq):
        ds = seq.parse(option(docstring, u''))
        a = seq.parse(option(annotation, Annotations([])))
        seq.parse(keyword('action'))
        n = name(seq)
        if n in self.names:
                throw_caty_exception(
                    u'CARA_PARSE_ERROR',
                    u'Duplicated action name: $name resource: $resource module: $module', 
                    name=n, resource=self.rcname, module=self._module_name)
        self.names.add(n)
        invoker = option(self.invoker)(seq)

        opts = option(object_)(seq)
        seq.parse('::')
        prof = option(try_(self.profile))(seq)
        links = option(self.links)(seq)
        seq.parse('{')
        start = seq.pos
        proxy = self._script_parser(seq)
        end = seq.pos
        seq.parse('}')
        lock = option(self.locks)(seq)
        if seq.current != ';':
            raise ParseError(seq, ';')
        seq.parse(';')
        source = seq.text[start:end].strip()
        rae = ResourceActionEntry(
                                  proxy, 
                                  source, 
                                  n, 
                                  ds, 
                                  a, 
                                  self.rcname, 
                                  self._module_name,
                                  prof)
        if lock:
            rae.set_lock_cmd(lock)
        generates = option(self.generates)(seq)
        if invoker in self.actions:
                throw_caty_exception(
                    u'CARA_PARSE_ERROR',
                    u'Duplicated action invoker: $invoker resource:$resource module: $module', 
                    invoker=invoker, resource=self.rcname, module=self._module_name)
        self.actions[invoker] = rae

    def invoker(self, seq):
        # XXX:verbの構文チェックが必要?
        seq.parse('(')
        pattern = seq.parse(string)
        seq.parse(')')
        return pattern.strip()
        

    def links(self, seq):
        seq.parse(keyword('links'))
        if seq.current == '[':
            seq.parse('[')
            r = split(self.link_item, ',', True)(seq)
            seq.parse(']')
            return r
        else:
            return [self.link_item(seq)]

    def link_item(self, seq):
        src = name(seq)
        seq.parse('-->')
        dest = name(seq)
        return src, dest

    def name(self, seq):
        return seq.parse(Regex(r'[a-zA-Z_][-a-zA-Z0-9_.:]*'))

    def generates(self, seq):
        seq.parse(keyword('generates'))
        name = seq.parse(Regex(r'[a-zA-Z_][-a-zA-Z0-9_]*'))
        seq.parse('{')
        start = seq.pos
        proxy = self._script_parser(seq)
        end = seq.pos
        seq.parse('}')
        seq.parse(';')
        return name

    def profile(self, seq):
        oi = option(typedef)(seq)
        i = option(self.inner_profile)(seq)
        if not oi and not i:
            raise ParseError(seq, self.profile)
        if oi:
            _ = seq.parse('->')
            oo = typedef(seq)
            return ActionProfile(oi, oo)
        else:
            return ActionProfile(inner_profile=i)

    def inner_profile(self, seq):
        seq.parse('-(')
        is_opt = option('*')(seq)
        i = typedef(seq)
        _ = seq.parse('->')
        o = typedef(seq)
        seq.parse(')')
        return (i, o, is_opt)

    def instance(self, seq):
        seq.parse(keyword('instance'))
        seq.parse(split(self.instance_name, ','))
        seq.parse(';')
        return None, None

    def instance_name(self, seq):
        seq.parse('"')
        seq.parse(until('"'))
        seq.parse('"')
        return

    def locks(self, seq):
        seq.parse(keyword('locks'))
        seq.parse('{')
        proxy = self._script_parser(seq)
        seq.parse('}')
        return proxy

def is_doc_str(seq):
    _ = seq.parse(option(docstring))
    if _:
        try:
            seq.parse(skip_ws)
            seq.parse(['resource', 'action'])
            return True
        except:
            return False
    return False


def name(seq):
    return seq.parse(Regex(r'[a-zA-Z_][-a-zA-Z0-9_]*'))

def string(seq):
    h = seq.ignore_hook
    try:
        seq.ignore_hook = True
        seq.parse('"')
        s = seq.parse(until(['"', '\n']))
        seq.parse('"')
        return s
    finally:
        seq.ignore_hook = h

