from caty.command import *
from caty.core.language import split_colon_dot_path
from caty.core.language.util import make_structured_doc
from caty.jsontools import tagged

class ListStates(Command):
    def setup(self, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self.__cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            module_name = _
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            return []
        r = []
        tmap = {
            'embeded-link':  u'embedded',
            'additional-link': u'additional',
            'no-cara-link': u'indef'
        }
        for s in module.states:
            links = {}
            for l in s.links:
                links[l.trigger] = tagged(u'link', {
                    'name': l.trigger,
                    'becoming': tmap[l.type],
                    'occurrence': l.appearance,
                    'target': map(lambda x:x[0], l.link_to_list)
                })
            r.append({
                'name': s.name,
                'document': make_structured_doc(s.docstr),
                'type': s.type.name,
                'links': links,
            })
        return r


