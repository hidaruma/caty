from caty.template.core.vm import VirtualMachine
from StringIO import StringIO
class Template(object):
    def __init__(self, bytecode_loader, schema_module):
        self._path = ''
        self._context = {}
        self._bytecode_loader = bytecode_loader
        self._vm = VirtualMachine(bytecode_loader, schema_module)

    def context():
        def _get(self):
            return self._context

        def _set(self, value):
            if isinstance(value, dict):
                self._context = {}
                self._context['_CONTEXT'] = value
                self._context.update(value)
            else:
                self._context = {'_CONTEXT': value}
        return _get, _set
    context = property(*context())

    def renderer():
        def get(self):
            return self._vm.renderer
        def set(self, renderer):
            self._vm.renderer = renderer
        return get, set
    renderer = property(*renderer())

    def __setitem__(self, key, value):
        self._context[key] = value

    def add_filter(self, filter, type):
        self._vm.filters.add(type, filter)

    def set_template(self, template_path):
        self._path = template_path
        self.code = self._bytecode_loader.load(self._path)

    def set_include_callback(self, handler):
        self._vm._include_callback = handler

    def set_filter_executor(self, executor):
        self._vm._filter_executor = executor

    def write(self, out):
        self._vm.context = self.context
        self._vm.write(self.code, out)

    def allow_undef():
        def _get(self):
            return self._vm.allow_undef
        def _set(self, value):
            self._vm.allow_undef = value
        return _get, _set
    allow_undef = property(*allow_undef())

