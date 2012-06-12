import sys
import json
import os

BASE_DIR = os.path.join('common', 'fit-view', 'pub/')
apps = {}
for r, d, fs in os.walk(BASE_DIR):
    for f in fs:
        if f.endswith('.fit'):
            c = open(os.path.join(r, f)).read()
            o = json.loads(unicode(c, 'utf-8'))
            if o['total'] != o['succ'] + o['indef']:
                path = os.path.join(r, f)
                app, name = path.replace(BASE_DIR, '').split(os.path.sep, 1)
                app = r.split(os.path.sep)[-1]
                name = f
                if app not in apps:
                    apps[app] = []
                apps[app].append({'path': name, 'result': o})

s = []
for app_name, app_result in apps.items():
    s.append(app_name+':')
    for v in app_result:
        r = v['result']
        s.append('  %s:%s' % (r['title'], v['path']))
        s.append('    OK: %d' % (r['succ']))
        s.append('    NG: %d' % (r.get('fail', 0)))
        s.append('    Indef: %d' % (r.get('indef', 0)))
        s.append('    Error: %d' % (r.get('error', 0)))
        s.append('    Invalid: %d' % (r.get('invalid',0 )))
        m = r['error_msg']
        if m:
            s.append('    Error Message:')
            for l in m.split('\n'):
                s.append('      '+l)
        s.append('\n')
res = '\n'.join(s).strip()
if not res:
    print 'OK'
    sys.exit(0)
else:
    print res.encode('UTF-8')
    sys.exit(1)

