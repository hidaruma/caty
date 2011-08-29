
def create_resource_action_dispatcher(action_fs, facility, app):
    from caty.core.action.module import ResourceModuleContainer
    from caty.core.action.parser import ResourceActionDescriptorParser, is_doc_str
    from caty.core.std.action import create_default_resources
    from caty.core.casm.language.util import remove_comment
    import caty.jsontools.xjson as xjson
    rmc = ResourceModuleContainer(app)
    for r in create_default_resources(facility):
        rmc.add_resource(r)
    if app._no_ambient:
        return rmc
    for f in action_fs.opendir(u'/').read(True):
        if not f.is_dir and f.path.endswith('.cara'):
            try:
                msg = app.i18n.get('Action: $path', path=f.path.strip('/'))
                app.cout.write(u'  * ' + msg)
                app.cout.write('...')
                source = f.read()
                parser = ResourceActionDescriptorParser(f.path.strip('/').split('.')[0].replace('/', '.'), facility)
                resource_module = parser.run(source, hook=lambda seq:remove_comment(seq, is_doc_str), auto_remove_ws=True)
                for res in resource_module.resources:
                    app.update_filetypes(res.filetypes)
                rmc.add_module(resource_module)
                app.cout.writeln('OK')
            except:
                app.cout.writeln('NG')
                raise
    return rmc


