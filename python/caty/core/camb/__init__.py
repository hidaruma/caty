# coding: utf-8

def create_bindings(action_fs, app):
    from caty.core.camb.parser import BindingParser, LiterateBindingParser
    from caty.core.camb.binding import ModuleBinderContainer
    from caty.core.language.util import remove_comment
    if app._no_ambient:
        return 
    binders = ModuleBinderContainer()
    for f in action_fs.opendir(u'/').read(True):
        if not f.is_dir and (f.path.endswith('.camb') or f.path.endswith('.camb.lit')):
            try:
                msg = app.i18n.get('Bindings: $path', path=f.path.strip('/'))
                app.cout.write(u'  * ' + msg)
                app.cout.write('...')
                source = f.read()
                if f.path.endswith('.camb.lit'):
                    parser = LiterateBindingParser(f.path.strip('/').split('.')[0].replace('/', '.'), binders, app)
                else:
                    parser = BindingParser(f.path.strip('/').split('.')[0].replace('/', '.'), binders, app)
                binder = parser.run(source, hook=lambda seq:remove_comment(seq, is_doc_str), auto_remove_ws=True)
                app.cout.writeln('OK')
            except:
                app.cout.writeln('NG')
                raise
    return binders

def is_doc_str(seq):
    from topdown import option, skip_ws
    from caty.core.language.util import docstring
    _ = seq.parse(option(docstring))
    if _:
        try:
            seq.parse(skip_ws)
            seq.parse(option(annotation))
            seq.parse(skip_ws)
            seq.parse(['bind'])
            return True
        except Exception, e:
            return False
    return False
