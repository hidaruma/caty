#coding:utf-8
from topdown import *
from caty.core.casm.language.casmparser import module_decl
from caty.core.casm.language.schemaparser import object_, typedef
from caty.core.casm.language.commandparser import resource, jump, CommandScriptParser
from caty.core.language.util import docstring, annotation, action_fragment_name, annotation, identifier_token, identifier_token_m, name_token, some_token, class_identifier_token, class_identifier_token_m
from xjson import obj
from caty.core.action.resource import ResourceClass
from caty.core.action.module import ResourceModule
from caty.core.action.entry import ResourceActionEntry, ActionProfiles, ActionProfile
from caty.core.schema.base import Annotations
from caty.core.casm.language import schemaparser, commandparser, constparser
from caty.core.casm.language.ast import Root, CommandNode, ConstDecl
from caty.util import bind2nd
from caty.core.exception import throw_caty_exception
from caty.core.language.util import make_structured_doc
from caty.core.exception import InternalException

class ResourceActionDescriptorParser(Parser):
    _literate = False
    def __init__(self, path, facility, fragment=False):
        self._script_parser = CommandScriptParser(facility)
        self._path = path
        self._app = facility.app
        self._fragment = fragment

    def __call__(self, seq):
        mn = module_decl(seq, 'cara', self._fragment)
        name = mn.name
        self._module_name = name
        ds = mn.docstring or u''
        if self._path.strip(u'/').split(u'.')[0].replace(u'/', u'.') != name:
            raise InternalException("Module name $name and path name $path are not matched", name=name, path=self._path)
        rm = ResourceModule(name.split('.')[-1], ds, self._app)
        rm.attaches = mn.attaches
        classes = seq.parse(many(map(try_, [self.resourceclass, self.state, schemaparser.schema, commandparser.command, constparser.const, self.userrole, self.port])))
        if not seq.eof:
            raise ParseError(seq, self)
        for c in classes:
            if isinstance(c, (Root, CommandNode, ConstDecl)):
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
        return StateBlock(ds, ann, self._script_parser)(seq)

    def userrole(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        return UserRole(ds, ann)(seq)

    def resourceclass(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        seq.parse(keyword('resource'))
        try:
            rcname = name_token(seq)
            url_pattern = self.url_pattern(seq)
            seq.parse('{')
            block = seq.parse(ResourceBodyBlock(rcname, self))
            actions = block.actions
            filetype = block.filetype
            instances = block.instances
            seq.parse('}')
            seq.parse(';')
            return ResourceClass(self._app, url_pattern, actions, filetype, instances, self._module_name, rcname, ds, ann)
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

class ResourceBodyBlock(Parser):
    def __init__(self, rcname, parent):
        self.rcname = rcname
        self.actions = {}
        self.instances = []
        self.filetype = {}
        self.names = set()
        self._script_parser = parent._script_parser
        self._module_name = parent._module_name
        self.parent = parent
        self.implemented = u'none'
        self._invoker = None

    def __call__(self, seq):
        option(self.filetype_)(seq)
        many(choice(self.action, self.instance))(seq)
        return self

    def filetype_(self, seq):
        seq.parse('filetype')
        o = seq.parse(obj)
        self.filetype['contentType'] = o['contentType']
        self.filetype['isText'] = o['isText']
        seq.parse(';')

    def action(self, seq):
        from caty.core.casm.language.ast import ObjectNode, SymbolNode
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

        opts = option(object_, ObjectNode({}))(seq)
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
            self.implemented = u'catyscript'
        rae = ResourceActionEntry(
                                  proxy, 
                                  source, 
                                  n, 
                                  ds, 
                                  a, 
                                  self,
                                  prof,
                                  invoker,
                                  self.implemented,
                                  opts)
        if lock:
            rae.set_lock_cmd(lock)
        generates = option(self.generates)(seq)
        if invoker in self.actions:
                throw_caty_exception(
                    u'CARA_PARSE_ERROR',
                    u'Duplicated action invoker: $invoker resource:$resource module: $module', 
                    invoker=invoker, resource=self.rcname, module=self._module_name)
        self._invoker = invoker
        self.actions[invoker] = rae

    def instance(self, seq):
        keyword(u'instance')(seq)
        if seq.current == u'"':
            self.instances.append(string(seq))
        else:
            S(u'[')(seq)
            self.instances.extend(split(string, u',', allow_last_delim=True)(seq))
            S(u']')(seq)
        S(u';')(seq)

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
        prof, jmp, fcl_usage = option(try_(self.profile), (None, [], []))(seq)
        profs = [p for p in option(split(self.internal_profile, ',', allow_last_delim=True), [])(seq) if p]
        if prof:
            return ActionProfiles([prof]+profs, jmp, fcl_usage)
        else:
            return ActionProfiles(profs, jmp, fcl_usage)

    def profile(self, seq):
        next_states = []
        relay_list = []
        redirects = []
        link = []
        in_type, out_type = option(try_(self.__io_type), (None, None))(seq)
        jmp = jump(seq)
        resource_decl = many(resource)(seq)
        link = unordered(self.relays, self.produces, self.redirects)(seq)
        for t, v in link:
            if t == 'relays':
                relay_list = v
            elif t == 'redirects':
                redirects = v
            elif t == 'produces':
                next_states = v
        if in_type:
            p = ActionProfile(u'whole', u'', in_type, out_type, relay_list, next_states, redirects)
        elif link:
            p = ActionProfile(u'whole', u'', u'_', u'_', relay_list, next_states, redirects)
        else:
            p = None
        return p, jmp, resource_decl

    def __io_type(self, seq):
        in_type = choice('_', typedef)(seq)
        seq.parse('->')
        out_type = choice('_', typedef)(seq)
        return in_type, out_type

    def internal_profile(self, seq):
        io_type, fragment = seq.parse(self.fragment_name)
        next_states = []
        relay_list = []
        redirects = []
        link = []
        in_type = choice('_', typedef)(seq)
        seq.parse('->')
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
        name = action_fragment_name(seq)
        if 'in' in ann:
            if 'out' in ann:
                pf = u'io'
            else:
                pf = u'in'
        elif 'out' in ann:
            pf = u'out'
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

    def locks(self, seq):
        seq.parse(keyword('locks'))
        seq.parse('{')
        proxy = self._script_parser(seq)
        seq.parse('}')
        return proxy

class StateBlock(Parser):
    def __init__(self, docstr=u'', annotations=Annotations([]), parser=None):
        self.annotations = annotations
        self.docstr = docstr
        self.modifier = u'state'
        self.merge = False
        self.link_name = u'links'
        self._script_parser = parser
        self.parent = None

    @property
    def docstring(self):
        return self.docstr

    def __call__(self, seq):
        seq.parse(keyword('state'))
        with strict():
            state_name = seq.parse(name)
            if option(keyword('for'))(seq):
                if option(peek(S('[')))(seq):
                    S('[')(seq)
                    self.actor_names = split(name, u',', allow_last_delim=True)(seq)
                    S(']')(seq)
                else:
                    self.actor_names = [seq.parse(name)]
            else:
                self.actor_names = []
            seq.parse('::')
            self.type = typedef(seq)
            if option(keyword('as'))(seq):
                self.modifier = name(seq)
            elif option(keyword('baseobject'))(seq):
                self.merge = True
                self.link_name = None
                self.modifier = None
            links = option(self.link_block, [])(seq)
            seq.parse(';')
            self.name = state_name
            self.links = links
            return self

    def link_block(self, seq):
        seq.parse(keyword('links'))
        if self.merge == False:
            if option(keyword('as'))(seq):
                self.link_name = name(seq)
        seq.parse('{')
        r = many(self.link_item)(seq)
        seq.parse('}')
        return r

    def link_item(self, seq):
        ds = seq.parse(option(docstring, u''))
        ann = seq.parse(option(annotation, Annotations([])))
        isembed, trigger, occ, path = self.trigger(seq)
        with strict():
            if option('::')(seq):
                typedef(seq)
            seq.parse('-->')
            if peek(option(S('[')))(seq):
                S('[')(seq)
                dest = split(self.state_ref, ',')(seq)
                S(']')(seq)
            else:
                dest = [self.state_ref(seq)]
            S(';')(seq)
            return Link(trigger, dest, isembed, occ, path, ds, ann)

    def trigger(self, seq):
        if option(S('+'))(seq):
            n = name(seq)
            o = option(choice([u'+', u'*', u'!', u'?']), u'!')(seq)
            p = None
            t = u'additional'
        elif option(S('-'))(seq):
            n = name(seq)
            o = option(choice([u'+', u'*', u'!', u'?']), u'!')(seq)
            p = None
            t = u'embed' 
        else:
            option(S('?'))(seq)
            n = name(seq)
            o = option(choice([u'+', u'*', u'!', u'?']), u'!')(seq)
            p = option(self.embed_trigger, n)(seq)
            t = u'indef'
        return t, n, o, p

    def embed_trigger(self, seq):
        return self._script_parser.command(seq, no_opt=True)

    def state_ref(self, seq):
        stname = class_identifier_token_m(seq)
        orelse = []
        if option(keyword(u'orelse'))(seq):
            if option(S(u'[')):
                orelse = split(class_identifier_token_m, ',')(seq)
                S(']')(seq)
            else:
                orelse = [class_identifier_token_m(seq)]
        if option(keyword(u'by'))(seq):
            cmd = class_identifier_token(seq)
        else:
            cmd = None
        return LinkDest(stname, orelse, cmd)

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

    def reify(self):
        return {
            "name": self.name,
            "document": make_structured_doc(self.docstr),
            "annotation": self.annotations.reify(),
            "actors": self.actor_names,
            "modifier": self.modifier,
            "isBaseobject": self.merge,
            "linkName": self.link_name,
            "links": [l.reify() for l in self.links],
            "type": self.type.reify()
        }

    @property
    def canonical_name(self):
        return self.parent.canonical_name + ':' + self.name

    @property
    def app(self):
        return self.parent.app

class LinkDest(object):
    def __init__(self, stname, orelse, cmd):
        self.main_transition = stname
        self.sub_transtion = orelse
        self.command = cmd

class UserRole(Parser):
    def __init__(self, ds, ann):
        self.docstring = ds
        self.annotations = ann

    def __call__(self, seq):
        keyword('userrole')(seq)
        self.name = name(seq)
        if option(u'=')(seq):
            self.typedef = typedef(seq)
        else:
            self.typedef = None
        S(';')(seq)
        return self

    def reify(self):
        return {
            "name": self.name,
            "document": make_structured_doc(self.docstring),
            "annotation": self.annotations.reify(),
        }


class Link(object):
    def __init__(self, trigger, dest, type, appearance, path, docstring=u'', annotations=Annotations([])):
        self.docstring = docstring
        self.annotations = annotations
        self.destinations = dest
        self.trigger = trigger
        self.path = path
        self.appearance = appearance
        if type == 'embed':
            self.type = u'embeded-link'
        elif type == 'indef':
            self.type = u'indef-link'
        else:
            self.type = u'additional-link'

    def reify(self):
        return {
            'trigger': self.trigger,
            'appearance': self.appearance,
            'links-to': self.link_to_list,
            'path': self.path,
            'type': self.type.replace('-link', '')
        }




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
    _literate = True
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
        self._module_name = name
        ds = mn.docstring or u''
        if self._path.strip(u'/').split(u'.')[0].replace(u'/', u'.') != name:
            raise InternalException("Module name $name and path name $path are not matched", name=name, path=self._path)
        rm = ResourceModule(name, ds, self._app)
        classes = self._parse_top_level(seq)
        rm._literate = True
        if not seq.eof:
            raise ParseError(seq, self)
        for c in classes:
            if isinstance(c, (Root, CommandNode, ConstDecl)):
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
            n = seq.parse(map(try_, [self.resourceclass, self.state, schemaparser.schema, commandparser.command, constparser.const, self.port, peek(S(u'}>>'))]))
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
                     constparser.const,
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
    

    def reify(self):
        return {
            "name": self.name,
            "document": make_structured_doc(self.docstring),
            "annotation": self.annotations.reify(),
        }


def is_doc_str(seq):
    _ = seq.parse(option(docstring))
    if _:
        try:
            seq.parse(skip_ws)
            seq.parse(option(annotation))
            seq.parse(skip_ws)
            seq.parse(['resource', 'action', 'module', 'state', 'port', 'command', 'type', 'const', _link_item_head])
            return True
        except Exception, e:
            return False
    return False

_dummy_state_block = StateBlock()
def _link_item_head(seq):
    if option(S('+'))(seq):
        seq.parse(skip_ws)
        n = name(seq)
        seq.parse(skip_ws)
        o = option(choice([u'+', u'*', u'!', u'?']), u'!')(seq)
    elif option(S('-'))(seq):
        seq.parse(skip_ws)
        n = name(seq)
        seq.parse(skip_ws)
        o = option(choice([u'+', u'*', u'!', u'?']), u'!')(seq)
    else:
        option(S('?'))(seq)
        seq.parse(skip_ws)
        n = name(seq)
        seq.parse(skip_ws)
        o = option(choice([u'+', u'*', u'!', u'?']), u'!')(seq)
    if option('::')(seq):
        typedef(seq)
    seq.parse(skip_ws)
    return S(u'-->')(seq)

