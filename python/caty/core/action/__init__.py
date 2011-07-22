
def create_resource_action_dispatcher(action_fs, facility, app):
    from caty.core.action.module import ResourceModuleContainer
    from caty.core.action.parser import ResourceActionDescriptorParser, is_doc_str
    from caty.core.std.action import create_default_resources
    from caty.core.casm.language.util import remove_comment
    import caty.jsontools.xjson as xjson
    rsc = ResourceModuleContainer(app)
    rsc.add(create_default_resources(facility))
    if app._no_ambient:
        return rsc
    for f in action_fs.opendir(u'/').read(True):
        if not f.is_dir and f.path.endswith('.cara'):
            try:
                msg = app.i18n.get('Action: $path', path=f.path.strip('/'))
                app.cout.write(u'  * ' + msg)
                app.cout.write('...')
                source = f.read()
                parser = ResourceActionDescriptorParser(f.path.strip('/').split('.')[0].replace('/', '.'), facility)
                resources = parser.run(source, hook=lambda seq:remove_comment(seq, is_doc_str), auto_remove_ws=True)
                for res in resources:
                    app.update_filetypes(res.filetypes)
                rsc.add(resources)
                app.cout.writeln('OK')
            except:
                app.cout.writeln('NG')
                raise
    return rsc


