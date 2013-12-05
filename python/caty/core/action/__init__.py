
def create_resource_action_dispatcher(action_fs, facility, app):
    from caty.core.action.module import ResourceModuleContainer
    rmc = ResourceModuleContainer(app)
    for r in app._system.system_resource_actions:
        rmc.add_resource(r)
    if app._no_ambient:
        return rmc
    orig = app._schema_module.fs
    app._schema_module.fs = action_fs
    read_cara_files(rmc, action_fs, facility, u'/', app)
    app._schema_module.fs = orig
    rmc.validate_url_patterns()
    return rmc

def read_cara_files(rmc, action_fs, facility, target, app, current_package=None):
    from caty.core.action.parser import ResourceActionDescriptorParser, is_doc_str, LiterateRADParser
    from caty.core.language.util import remove_comment
    import xjson
    for f in action_fs.opendir(target).read():
        if not f.is_dir and (f.path.endswith('.cara') 
                            or f.path.endswith('.cara.lit') 
                            or f.path.endswith('.cara.frag')
                            or f.path.endswith('.cara.frag.lit')):
            try:
                msg = app.i18n.get('Action: $path', path=f.path.strip('/'))
                app.cout.write(u'  * ' + msg)
                app.cout.write('...')
                source = f.read()
                if f.path.endswith('.lit'):
                    parser = LiterateRADParser(f.path, facility, '.cara.frag' in f.path)
                else:
                    parser = ResourceActionDescriptorParser(f.path, facility, '.cara.frag' in f.path)
                resource_module = parser.run(source, hook=lambda seq:remove_comment(seq, is_doc_str), auto_remove_ws=True)
                if current_package:
                    resource_module.parent = current_package
                    current_package.add_sub_module(resource_module)
                else:
                    resource_module.parent = app._schema_module
                    app._schema_module.add_sub_module(resource_module)
                for res in resource_module.resources:
                    app.update_filetypes(res.filetypes)
                rmc.add_module(resource_module)
                app.cout.writeln('OK')
            except:
                app.cout.writeln('NG')
                raise
        elif f.is_dir:
            parent = app._schema_module if not current_package else current_package
            pkg = parent._compile_dir(f, ResPackage)
            pkg._type = u'cara'
            read_cara_files(rmc, action_fs, facility, f.path, app, pkg)

from caty.core.casm.module import Package
class ResPackage(Package):
    type = u'cara'
    def compile(self):
        pass
