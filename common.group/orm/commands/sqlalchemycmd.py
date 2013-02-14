from caty.command import *
from caty.core.typeinterface import dereference
from caty.util.path import join

class CreateClassFromType(Command):
    def setup(self, opts, typename):
        self.__debug = opts['debug']
        self.__typename = typename

    def execute(self):
        type = self.schema.get_type(self.__typename)
        t = type
        if t.type != 'object':
            throw_caty_exception(u'InvalidInput', t.type)
        fname = type.name + '.py'
        clsname = type.name
        py_class = self.sqlalchemy.generate_py_class(t, clsname)
        if self.__debug:
            print py_class
        app_info = self.env['APPLICATION']
        prj_info = self.env['PROJECT']
        lib_path = join(prj_info['location'], app_info['group']+'.group', app_info['name'], u'lib', fname)
        open(lib_path, 'wb').write(py_class)

class MapTable(Command):
    def setup(self, typename):
        self.__typename = typename

    def execute(self):
        type = self.schema.get_type(self.__typename)
        clsname = type.name
        gdict = {'__file__': __file__}
        exec 'from %s import %s as cls' % (clsname, clsname) in gdict
        self.sqlalchemy.create_table(gdict['cls'])
        
        

