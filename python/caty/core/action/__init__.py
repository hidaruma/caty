
def create_resource_action_dispatcher(action_fs, facility, app):
    from caty.core.action.module import ResourceModuleContainer
    from caty.core.std.action import create_default_resources
    rmc = ResourceModuleContainer(app)
    for r in create_default_resources(facility):
        rmc.add_resource(r)
    if app._no_ambient:
        return rmc
    read_cara_files(rmc, action_fs, facility, u'/', app)
    rmc.validate_url_patterns()
    return rmc

def read_cara_files(rmc, action_fs, facility, target, app, current_package=None):
    from caty.core.action.parser import ResourceActionDescriptorParser, is_doc_str, LiterateRADParser
    from caty.core.language.util import remove_comment
    import caty.jsontools.xjson as xjson
    for f in action_fs.opendir(target).read():
        if not f.is_dir and (f.path.endswith('.cara') or f.path.endswith('.cara.lit')):
            try:
                msg = app.i18n.get('Action: $path', path=f.path.strip('/'))
                app.cout.write(u'  * ' + msg)
                app.cout.write('...')
                source = f.read()
                if f.path.endswith('.cara.lit'):
                    parser = LiterateRADParser(f.path.strip('/').split('.')[0].replace('/', '.'), facility)
                else:
                    parser = ResourceActionDescriptorParser(f.path.strip('/').split('.')[0].replace('/', '.'), facility)
                resource_module = parser.run(source, hook=lambda seq:remove_comment(seq, is_doc_str), auto_remove_ws=True)
                for res in resource_module.resources:
                    app.update_filetypes(res.filetypes)
                rmc.add_module(resource_module)
                if current_package:
                    current_package.add_sub_module(resource_module)
                app.cout.writeln('OK')
            except:
                app.cout.writeln('NG')
                raise
        elif f.is_dir:
            orig = app._schema_module.fs
            app._schema_module.fs = action_fs
            pkg = app._schema_module._compile_dir(f, ResPackage)
            pkg._type = u'cara'
            app._schema_module.fs = orig
            read_cara_files(rmc, action_fs, facility, f.path, app, pkg)

from caty.core.casm.module import Package
class ResPackage(Package):
    def compile(self):
        pass
