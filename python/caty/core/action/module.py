#coding :utf-8
from caty.core.action.selector import *
from caty.core.action.resource import *
from caty.core.exception import *

class ResourceModuleContainer(object):
    def __init__(self, app):
        self._app = app
        self._selectors = [ResourceSelector(app),
                           ResourceSelector(app),
                           ResourceSelector(app),
                          ]
    
    def add(self, resource_classes):
        for r in resource_classes:
            self._selectors[r.type].add(r)

    def get(self, fs, path, verb, method, no_check=False):
        v = self._verify(fs, path)
        if v:
            return v
        for s in self._selectors:
            matched = s.get(fs, path, verb, method, no_check)
            if matched:
                return matched.resource_class_entry
        throw_caty_exception(
            u'HTTP_403',
            u'Not matched to verb dispatch: path=$path, verb=$verb, method=$method',
            path=path,
            verb=verb,
            method=method)

    def _verify(self, fs, path):
        if not path.endswith('/') and fs.open(path + '/').exists:
            if self._app.web_config['missingSlash'] == 'dont-care':
                if fs.application.name != 'root':
                    return ResourceActionEntry(None, u'http:not-found /%s%s' % (fs.application.name, path), u'not-found')
                return ResourceActionEntry(None, u'http:not-found %s' % (path), u'not-found')
            if fs.application.name != 'root':
                return ResourceActionEntry(None, u'http:found /%s%s/' % (fs.application.name, path), u'not-found')
            return ResourceActionEntry(None, u'http:found %s/' % (path), u'not-found')
        return None

    def _get_trace(self, fs, path, verb, method, no_check=False):
        trace = []
        v = self._verify(fs, path)
        if v:
            for s in self._selectors[:-1]:
                trace.append(None)
            trace.append(u'system:missingSlash._')
            return trace
        matched = None
        for s in self._selectors:
            if matched:
                trace.append(None)
            else:
                _matched = s.get(fs, path, verb, method, no_check)
                if _matched:
                    matched = _matched
                    trace.append(u'%s:%s.%s' % (matched.module_name, matched.resource_name, matched.name))
                else:
                    trace.append(False)
        return trace

    def __repr__(self):
        return repr(self._ftd)

    def get_resource(self, name):
        for s in self._selectors:
            r = s.get_resource(name)
            if r:
                return r
        return None

class ResourceModule(list):
    def __init__(self, name, docstring):
        self.name = name
        self.docstring = docstring
        list.__init__(self)

