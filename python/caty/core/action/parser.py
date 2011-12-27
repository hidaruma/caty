#coding:utf-8
from topdown import *
from caty.core.script.parser import ScriptParser
from caty.core.casm.language.casmparser import module_decl
from caty.core.casm.language.schemaparser import object_, typedef
from caty.core.language.util import docstring, annotation, fragment_name, annotation, identifier_token, identifier_token_m, name_token, some_token
from caty.jsontools.xjson import obj
from caty.core.action.resource import ResourceClass
from caty.core.action.module import ResourceModule
from caty.core.action.entry import ResourceActionEntry, ActionProfiles, ActionProfile
from caty.core.schema.base import Annotations
from caty.core.casm.language import schemaparser, commandparser
from caty.core.casm.language.ast import ASTRoot, CommandNode
from caty.util import bind2nd
from caty.core.exception import throw_caty_exception

class ResourceActionDescriptorParser(Parser):
    def __init__(self, module_name, facility, lit=False):
        self._script_parser = ScriptParser(facility)
        self._module_name = module_name
        self._app = facility.app
        self._lit = lit

    def __call__(self, seq):
        mn = module_decl(seq, 'cara')
        name = mn.name
        ds = mn.docstring or u'undocumented'
        if name != self._module_name:
            raise ParseFailed(seq, self, u'module name mismatched: %s' % name)
        rm = ResourceModule(name, ds, self._app)
        classes = seq.parse(many(map(try_, [self.resourceclass, self.state, schemaparser.schema, commandparser.command, self.userrole, self.port])))
        if not seq.eof:
            raise ParseError(seq, self)
        for c in classes:
            if isinstance(c, (ASTRoot, CommandNode)):
                c.declare(rm)
            else:
                if isinstance(c, ResourceClass):
                    rm.add_resource(c)
                elif isinstance(c, StateBlock):
                    rm.add_state(c)
                elif isinstance(c, UserRole):
                    rm.add_userrole(c)
                elif isinstance(c, Port):
                    rm.add_port(c)
        return rm

    def state(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        return StateBlock(ds, ann)(seq)

    def userrole(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        return UserRole()(seq)

    def resourceclass(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        seq.parse(keyword('resource'))
        try:
            rcname = name_token(seq)
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
        patterns = seq.parse(split(url_string, '|'))
        seq.parse(')')
        return u'|'.join(patterns)

    def port(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        keyword(u'port')(seq)
        n = name(seq)
        S(';')(seq)
        return Port(n, ds, ann)

def url_string(seq):
    try:
        ih = seq.ignore_hook
        seq.ignore_hook = True
        seq.parse(u'"')
        u = seq.parse(url_pattern)
    finally:
        seq.ignore_hook = ih
    seq.parse(u'"')
    return u''.join(u)

def url_pattern(seq):
    s = seq.pos
    last_seq = u''
    r = []
    while seq.current != '"' and not seq.eof:
        c = choice(u'**', u'*', u'/', ur'\"', Regex(ur'[^*/\"]+'))(seq)
        if ((c == u'/' and last_seq == u'/') or 
            (c == u'*' and last_seq in (u'**', u'*'))):
            raise ParseError(seq, url_pattern)
        last_seq = c
        r.append(c)
    return r

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
        return identifier_token_m(seq)

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
        profs = [p for p in split(self.profile, ',', allow_last_delim=True)(seq) if p]
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
        #if not io_type:
        #    return None
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
            return None, name
        return pf, name

    def relays(self, seq):
        p = seq.parse(keyword('relays'))
        return p, choice(self.one_name, self.list_name)(seq)

    def produces(self, seq):
        p = seq.parse(keyword('produces'))
        return p, choice(self.one_state, self.list_state)(seq)

    def redirects(self, seq):
        p = seq.parse(keyword('redirects'))
        return p, choice(self.one_state, self.list_state)(seq)

    def one_state(self, seq):
        return [self.name(seq)]

    def list_state(self, seq):
        seq.parse('[')
        r = split(self.name, ',', allow_last_delim=True)(seq)
        seq.parse(']')
        return r

    def one_name(self, seq):
        return [some_token(seq)]

    def list_name(self, seq):
        seq.parse('[')
        r = split(some_token, ',', allow_last_delim=True)(seq)
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
    def __init__(self, docstr=u'undocumented', annotations=Annotations([])):
        self.annotations = annotations
        self.docstr = docstr

    def __call__(self, seq):
        seq.parse(keyword('state'))
        state_name = seq.parse(name)
        if option(keyword('for'))(seq):
            if option(peek(S('[')))(seq):
                S('[')(seq)
                self.actor_names = split(name, u',', allow_last_delim=True)(seq)
                S(']')(seq)
            else:
                self.actor_names = [seq.parse(name)]
        else:
            self.actor_names = [u'']
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
        if peek(option(S('[')))(seq):
            S('[')(seq)
            dest = split(self.action_ref, ',')(seq)
            S(']')(seq)
        else:
            dest = [self.action_ref(seq)]
        S(';')(seq)
        return Link(trigger, dest, isembed)

    def trigger(self, seq):
        if option(S('+'))(seq):
            return 'additional', option(name)(seq)
        elif option(S('-'))(seq):
            return 'no-care', option(name)(seq)
        else:
            return 'embed', self.embed_trigger(seq)

    def embed_trigger(self, seq):
        return seq.parse(choice(Regex(ur'(\$\.)?([a-zA-Z_][a-zA-Z0-9_-]*(\(\))?\.)*[a-zA-Z_][a-zA-Z0-9_-]*(\(\))?'), '$'))

    def action_ref(self, seq):
        actname = identifier_token_m(seq)
        ref = seq.parse(option(Regex(r'(#(io|in)[0-9a-zA-Z_-]*)?')))
        if ref:
            return actname, ref
        else:
            return (actname, None)

    @property
    def label(self):
        if self.actor_name:
            return u'{0}\\n[{1}]'.format(self.name, self.actor_name)
        else:
            return self.name

    def make_label(self, module):
        if not self.actor_name:
            return self.name
        l = []
        for a in self.actor_names:
            for u in module.userroles:
                if a == u.name:
                    l.append(a)
                    break
            else:
                l.append(a+'?')
        return u'{0}\\n[{1}]'.format(self.name, u', '.join(l))

    @property
    def actor_name(self):
        return u', '.join(self.actor_names)

class UserRole(Parser):
    def __call__(self, seq):
        keyword('userrole')(seq)
        self.name = name(seq)
        S(';')(seq)
        return self

class Link(object):
    def __init__(self, trigger, dest, type):
        self.link_to_list = dest
        self.trigger = trigger
        if type == 'embed':
            self.type = u'embeded-link'
        elif type == 'no-care':
            self.type = u'no-care-link'
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
    return name_token(seq)

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

class LiterateRADParser(ResourceActionDescriptorParser):
    def __call__(self, seq):
        h = seq.ignore_hook
        seq.ignore_hook = True
        while True:
            x = until(u'<<{')(seq)
            S(u'<<{')(seq)
            if x.endswith('~'):
                continue
            break
        seq.ignore_hook = h
        mn = module_decl(seq, 'cara')
        name = mn.name
        ds = mn.docstring or u'undocumented'
        if name != self._module_name:
            raise ParseFailed(seq, self, u'module name mismatched: %s' % name)
        rm = ResourceModule(name, ds, self._app)
        classes = self._parse_top_level(seq)
        if not seq.eof:
            raise ParseError(seq, self)
        for c in classes:
            if isinstance(c, (ASTRoot, CommandNode)):
                c.declare(rm)
            else:
                if isinstance(c, ResourceClass):
                    rm.add_resource(c)
                elif isinstance(c, StateBlock):
                    rm.add_state(c)
                elif isinstance(c, UserRole):
                    rm.add_userrole(c)
                elif isinstance(c, Port):
                    rm.add_port(c)
        return rm

    def _parse_top_level(self, seq):
        s = []
        while not seq.eof:
            n = seq.parse(map(try_, [self.resourceclass, self.state, schemaparser.schema, commandparser.command, self.port, peek(S(u'}>>'))]))
            if n == u'}>>':
                break
            s.append(n)
        until(u'}>>')(seq)
        S(u'}>>')(seq)
        literal = True
        while not seq.eof:
            h = seq.ignore_hook
            seq.ignore_hook = True
            while literal:
                x = until(u'<<{')(seq)
                if seq.eof:
                    break
                S(u'<<{')(seq)
                if x.endswith('~'):
                    continue
                literal = False
            if seq.eof:
                break
            seq.ignore_hook = h
            elems = seq.parse(
                many(map(try_, 
                    [self.resourceclass, 
                     self.state, 
                     schemaparser.schema, 
                     commandparser.command, 
                     self.port])))
            for e in elems:
                s.append(e)
            S(u'}>>')(seq)
            literal = True
        return s


class Port(object):
    def __init__(self, name, doc, annotations):
        self._name = name
        self._doc = doc
        self._annotations = annotations

    @property
    def name(self):
        return self._name

    @property
    def annotations(self):
        return self._annotations

    @property
    def docstring(self):
        return self._doc
    


