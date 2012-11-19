#coding: utf-8
from caty.core.action.entry import ResourceActionEntry
from caty.core.action.resource import DefaultResource
from caty.core.script.parser import ScriptParser
from caty.core.schema.base import Annotations
from caty.core.action.module import ResourceModule

def create_default_resources(module):
    _script_actions(module) 
    _dir_actions(module) 
    _file_actions(module) 
    _template_actions(module) 

def _script_actions(module):
    parser = ScriptParser()
    rbody = DummyResourceBodyBlock(module, u'script', u'Script file')
    actions = {
        u'/GET#exists': ResourceActionEntry(parser.parse(u'call %0'), u'call %0', u'get', rbody=rbody),
        u'/POST#exists': ResourceActionEntry(parser.parse(u'call %0'), u'call %0', u'post', rbody=rbody),
        u'/PUT#exists': ResourceActionEntry(parser.parse(u'webio:not-allowed %0 PUT'), u'webio:not-allowed %0 PUT', u'put', rbody=rbody),
        u'/DELETE#exists': ResourceActionEntry(parser.parse(u'webio:not-allowed %0 PUT'), u'webio:not-allowed %0 DELETE', u'delete', rbody=rbody),
    }
    r = DefaultResource(module.app, u'**.cgi|**.act|**.do', actions, rbody._module_name, rbody.rcname, rbody.docstring, rbody.annotations)
    module.add_resource(r)

def _dir_actions(module):
    parser = ScriptParser()
    rbody = DummyResourceBodyBlock(module, u'dir', u'Directory')
    actions = {
        u'/GET#exists': ResourceActionEntry(parser.parse(u'dir-index %0 GET'), u'dir-index %0', u'get', rbody=rbody),
    }
    r = DefaultResource(module.app, u'**/|/', actions, rbody._module_name, rbody.rcname, rbody.docstring, rbody.annotations)
    module.add_resource(r)

def _file_actions(module):
    parser = ScriptParser()
    rbody = DummyResourceBodyBlock(module, u'file', u'Misc files')
    actions = {
        u'/GET#exists': ResourceActionEntry(parser.parse(u'print --raw %0'), u'print --raw %0', u'get', rbody=rbody),
    }
    r = DefaultResource(module.app, u'**.*|**', actions, rbody._module_name, rbody.rcname, rbody.docstring, rbody.annotations)
    module.add_resource(r)

def _template_actions(module):
    parser = ScriptParser()
    rbody = DummyResourceBodyBlock(module, u'template', u'Template files')
    actions = {
        u'/GET#exists': ResourceActionEntry(parser.parse(u'print %0'), u'print %0', u'get', rbody=rbody),
    }
    r = DefaultResource(module.app, u'**.html|**.xhtml|**.xml|**.htm', actions, rbody._module_name, rbody.rcname, rbody.docstring, rbody.annotations)
    module.add_resource(r)

class DummyResourceBodyBlock(object):
    def __init__(self, module, rcname, doc):
        self._module_name = module.name
        self.rcname = rcname
        self.docstring = doc
        self._annotations = Annotations([])
        self.parent = module

    @property
    def annotations(self):
        return self._annotations

