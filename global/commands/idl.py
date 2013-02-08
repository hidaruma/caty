from reification import *
import os

class GeneratePyClass(Command):
    def execute(self, cls_data):
        if not cls_data.get('anno', {}).get('signature', False):
            throw_caty_exception(u'InvalidInput', u'$$.anno.signature=$val', val=cls_data.get('anno', {}).get('signature', u'undefined'))
        name = cls_data['name']
        app_name = cls_data['location']['app'].strip('::')
        module_name = (cls_data['location']['pkg'] + cls_data['location']['mod']).strip(':')

        reifier = ShallowReifier()
        system = self.current_app._system
        app = system.get_app(app_name)
        module = app._schema_module.get_module(module_name)
        cls = module.get_class(name)
        r = []
        for c in cls.command_ns.values():
            r.append(reifier.reify_command(c))
        src = u'\n'.join(list(self._generate(name, r)))
        return {
            u'source': src,
            u'moduleName': u'interfaces.%s.%s' % (module_name, name)
        }



    def _generate(self, cls_name, commands):
        yield u'from caty.core.spectypes import UNDEFINED'
        yield u'from caty.core.facility import Facility, AccessManager'
        yield u'\n'
        yield u'class %sBase(Facility):' % cls_name
        yield u'    am = AccessManager()'
        for c in commands:
            name = c['name'].replace('-', '_')
            input_type = c['profile']['input']
            if not input_type.endswith(']'):
                throw_caty_exception(u'InvalidInput', u'Input type must be array type')
            input_types = input_type.strip('[]').split(',')
            anno = c.get('anno', {})
            if anno.get('reader'):
                yield u'    @am.read'
            elif anno.get('updater'):
                yield u'    @am.update'
            a1 = []
            a2 = []
            for i in input_types:
                n = i.split(' ')
                if n[0].endswith('?'):
                    a1.append('%s=UNDEFINED' % n[-1].strip(' '))
                    a2.append(n[-1].strip())
                elif n[0].endswith('*'):
                    a1.append('*%s' % n[-1].strip())
                    a2.append('*%s' % n[-1].strip())
                else:
                    a1.append(n[-1].strip())
                    a2.append(n[-1].strip())
            yield u'    def %s(self, %s):' % (name, u', '.join(a1))
            yield u'        return _%s(%s)' % (name, u', '.join(a2))
            yield u''
            yield u'    def _%s(self, %s):' % (name, u', '.join(a1))
            yield u'        raise NotImplementedError(u"%s._%s")' % (cls_name, name)
            yield u''




class WritePyClass(Command):
    def execute(self, data):
        pkg_dir = None
        chunk = data['moduleName'].split('.')
        p = [u'']
        for c in chunk[:-1]:
            p.append(c)
            path = u'/'.join(p)
            dir = self.sysfiles.lib.opendir(path)
            if not dir.exists:
                dir.create()
        p.append(chunk[-1])
        path = u'/'.join(p) + '.py'
        with self.sysfiles.lib.open(path, 'wb') as f:
            f.write(data['source'])

