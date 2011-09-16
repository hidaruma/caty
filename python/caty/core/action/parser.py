#coding:utf-8
from topdown import *
from caty.core.script.parser import ScriptParser
from caty.core.casm.language.casmparser import module_decl
from caty.core.casm.language.schemaparser import object_, typedef
from caty.core.language.util import docstring, annotation, fragment_name, annotation
from caty.jsontools.xjson import obj
from caty.core.action.resource import ResourceClass
from caty.core.action.module import ResourceModule
from caty.core.action.entry import ResourceActionEntry, ActionProfiles, ActionProfile
from caty.core.schema.base import Annotations
from caty.util import bind2nd
from caty.core.exception import throw_caty_exception

class ResourceActionDescriptorParser(Parser):
    def __init__(self, module_name, facility):
        self._script_parser = ScriptParser(facility)
        self._module_name = module_name
        self._app = facility.app

    def __call__(self, seq):
        mn = module_decl(seq, 'cara')
        name = mn.name
        ds = mn.docstring or u'undocumented'
        if name != self._module_name:
            raise ParseFailed(seq, self, u'module name mismatched: %s' % name)
        rm = ResourceModule(name, ds, self._app.name)
        classes = seq.parse(many([self.resourceclass, self.state]))
        if not seq.eof:
            raise ParseError(seq, self)
        for c in classes:
            for r in rm.resources:
                if r.name == c.name:
                    throw_caty_exception(
                        u'CARA_PARSE_ERROR',
                        u'Duplicated resource name: $name module: $module', 
                        name=c.name, module=name)

            if isinstance(c, ResourceClass):
                rm.resources.append(c)
            else:
                rm.states.append(c)
        return rm

    def state(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        return StateBlock()(seq)

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
        prof = option(try_(self.profiles))(seq)
        c = choice('{', ';')(seq)
        if c == ';':
            source = u'pass'
            proxy = self._script_parser.run(source, auto_remove_ws=True)
            lock = None
        else:
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
                                  prof,
                                  invoker)
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

    def profiles(self, seq):
        profs = split(self.profile, ',', allow_last_delim=True)(seq)
        return ActionProfiles(profs)

    def profile(self, seq):
        io_type, fragment = seq.parse(self.fragment_name)
        next_states = []
        relay_list = []
        redirects = []
        link = []
        if io_type in ('in', 'io'):
            in_type = typedef(seq)
        else:
            in_type = choice('_', typedef)(seq)
        seq.parse('->')
        if io_type in ('out', 'io'):
            out_type = option(typedef)(seq)
        else:
            out_type = choice('_', typedef)(seq)
        if io_type == 'in':
            link = unordered(self.relays, self.redirects)(seq)
        if io_type in ('io', 'out'):
            link = unordered(self.produces, self.redirects)(seq)
        for t, v in link:
            if t == 'relays':
                relay_list = v
            elif t == 'redirects':
                redirects = v
            elif t == 'produces':
                next_states = v
        return ActionProfile(io_type, fragment, in_type, out_type, relay_list, next_states, redirects)

    def fragment_name(self, seq):
        ann = annotation(seq)
        name = fragment_name(seq)
        if 'in' in ann:
            if 'out' in ann:
                pf = 'io'
            else:
                pf = 'in'
        elif 'out' in ann:
            pf = 'out'
        else:
            raise ParseError(seq, self.fragment_name)
        return pf, name

    def relays(self, seq):
        p = seq.parse(option(keyword('relays')))
        if p:
            return p, choice(self.one_state, self.list_state)(seq)
        return p, []

    def produces(self, seq):
        p = seq.parse(option(keyword('produces')))
        if p:
            return p, choice(self.one_state, self.list_state)(seq)
        return p, []

    def redirects(self, seq):
        p = seq.parse(option(keyword('redirects')))
        if p:
            return p, choice(self.one_state, self.list_state)(seq)
        return p, []

    def one_state(self, seq):
        return [self.name(seq)]

    def list_state(self, seq):
        seq.parse('[')
        r = split(self.name, ',', allow_last_delim=True)(seq)
        seq.parse(']')
        return r

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

class StateBlock(Parser):
    def __call__(self, seq):
        seq.parse(keyword('state'))
        state_name = seq.parse(name)
        seq.parse('::')
        type = typedef(seq)
        links = option(self.link_block, [])(seq)
        seq.parse(';')
        self.name = state_name
        self.links = links
        return self

    def link_block(self, seq):
        seq.parse(keyword('links'))
        seq.parse('{')
        r = many(self.link_item)(seq)
        seq.parse('}')
        return r

    def link_item(self, seq):
        isembed, trigger = self.trigger(seq)
        seq.parse('-->')
        dest = split(self.action_ref, ',')(seq)
        S(';')(seq)
        return Link(trigger, dest, isembed)

    def trigger(self, seq):
        if option(S('+'))(seq):
            return False, option(name)(seq)
        else:
            return True, self.embed_trigger(seq)

    def embed_trigger(self, seq):
        return seq.parse(choice(Regex(ur'(\$\.)?([a-zA-Z_][a-zA-Z0-9_-]*(\(\))?\.)*[a-zA-Z_][a-zA-Z0-9_-]*(\(\))?'), '$'))

    def action_ref(self, seq):
        ref = seq.parse(Regex(r'([a-zA-Z_][-a-zA-Z0-9_]*:)?[a-zA-Z_][-a-zA-Z0-9_]*\.[a-zA-Z_][-a-zA-Z0-9_]*(#(io|in)[0-9a-zA-Z_-]*)?'))
        if '#' in ref:
            return ref.split('#')
        else:
            return (ref, None)

class Link(object):
    def __init__(self, trigger, dest, isembed):
        self.link_to_list = dest
        self.trigger = trigger
        if isembed:
            self.type = u'embeded-link'
        else:
            self.type = u'additional-link'

def is_doc_str(seq):
    _ = seq.parse(option(docstring))
    if _:
        try:
            seq.parse(skip_ws)
            seq.parse(['resource', 'action', 'module'])
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

