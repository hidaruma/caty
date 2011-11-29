# coding: utf-8

def create_bindings(action_fs, app):
    from caty.core.camb.parser import BindingParser, LiterateBindingParser
    if app._no_ambient:
        return 
    for f in action_fs.opendir(u'/').read(True):
        if not f.is_dir and (f.path.endswith('.camb') or f.path.endswith('.camb.lit')):
            try:
                msg = app.i18n.get('Bindings: $path', path=f.path.strip('/'))
                app.cout.write(u'  * ' + msg)
                app.cout.write('...')
                source = f.read()
                if f.path.endswith('.camb.lit'):
                    parser = LiterateBindingParser(f.path.strip('/').split('.')[0].replace('/', '.'), app)
                else:
                    parser = BindingParser(f.path.strip('/').split('.')[0].replace('/', '.'), app)
                app.cout.writeln('OK')
            except:
                app.cout.writeln('NG')
                raise
    return 


