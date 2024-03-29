#coding: utf-8
from caty.core.exception import *
from caty.util.path import splitext, dirname, join
from caty.util.collection import merge_dict
from caty.core.action.resource import DefaultResource
from caty.core.action.entry import ResourceActionEntry
from caty.core.schema.base import Annotations

def resource_class_from_assocs(assocs, facility, app):
    from caty.core.action.module import ResourceModule
    from caty.core.std.action import DummyResourceBodyBlock
    classes = []
    ip = app._interpreter.file_mode(facility).start()
    rm = ResourceModule(u'_filetypes', u'', app)
    for path, patterns in assocs.items():
        actions = {}
        rbody = DummyResourceBodyBlock(rm, _to_resource_name(path), app._filetypes.get(path, {}).get('description'))
        p = _to_action_path_pattern(path)
        for k, v in patterns.items():
            if k == '':
                k = u'/GET'
            try:
                actions[k] = ResourceActionEntry(ip._compile(v), 
                                                v, 
                                                _to_action_name(k),
                                                rbody=rbody 
                                                )
            except:
                app.i18n.write("Failed to compile association: $app_name, $path_pattern", app_name=app.name, path_pattern=path+' '+k)
                raise

        classes.append(DefaultResource(app, p, actions, rbody._module_name, rbody.rcname, rbody.docstring, rbody.annotations))
    return classes

def _to_action_name(key):
    if not '/' in key:
        raise Exception()
    a, b = key.split('/')
    return u'_' if not a else a

def _to_resource_name(key):
    if key == '*':
        return u'File'
    if key == '*/':
        return u'Dir'
    prefix = 'Dir' if key.endswith('/') else 'File'
    return prefix + key.replace('_', '__').replace('.', '_D')

def _to_action_path_pattern(p):
    if p.startswith('.'):
        return u'*' + p.lower()
    else:
        return p.lower()

class DispatchError(Exception): pass


