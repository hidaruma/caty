from caty.command import Command
from caty.util.path import join
import caty.jsontools as json

class CheckFiles(Command):
    def setup(self, path):
        self._path = path

    def execute(self, dirdesc):
        r = self._check(dirdesc, 
                        '', 
                        {
                            'requiredFiles': [], 
                            'missingFiles': [], 
                            'optionalFiles': [],
                            'unwantedFiles': [],
                            'requiredDirs': [], 
                            'missingDirs': [], 
                            'optionalDirs': [],
                            'unwantedDirs': [],
                        })
        if r['missingFiles'] or r['unwantedFiles'] or r['missingDirs'] or r['unwantedDirs']:
            return json.tagged('NG', r)
        else:
            return json.tagged('OK', r)

    def _check(self, dirdesc, parent, res):
        entries = self.pub.opendir(join(self._path, parent)).read()
        files = []
        directories = []
        for e in entries:
            if e.is_dir:
                directories.append(e)
            else:
                files.append(e)

        for path, desc in sorted(dirdesc.items(), cmp=self._compare_path_pattern):
            if isinstance(desc, basestring):
                if path.startswith('*'):
                    ext = path.split('.')[-1] if '.' in path else u'*'
                    found = []
                    for ent in files:
                        if ext == u'*' or ent.basename.split('.')[-1] == ext:
                            found.append(ent)
                    if not found and desc == 'required':
                        res['missingFiles'].append(join(parent, path).lstrip('/'))
                    for f in found:
                        files.remove(f)
                        if desc == 'optional':
                            res['optionalFiles'].append(join(parent, f.basename).lstrip('/'))
                        else:
                            res['requiredFiles'].append(join(parent, f.basename).lstrip('/'))
                else:
                    found = []
                    for ent in files:
                        if ent.basename == path:
                            found.append(ent)
                            break
                    if not found and desc == 'required':
                        res['missingFiles'].append(join(parent, path).lstrip('/'))
                    for f in found:
                        files.remove(f)
                        if desc == 'optional':
                            res['optionalFiles'].append(join(parent, path).lstrip('/'))
                        else:
                            res['requiredFiles'].append(join(parent, path).lstrip('/'))
            else:
                desc, dirent = json.split_tag(desc)
                if path.startswith('*'):
                    ext = path.split('.')[-1] if '.' in path else u''
                    found = []
                    for ent in directories:
                        if ext == u'' or ent.basename.split('.')[-1] == ext:
                            if dirent is not None:
                                self._check(dirent, join(parent, ent.basename).lstrip('/'), res)
                            found.append(ent)
                    if not found and desc == 'required':
                        res['missingDirs'].append(join(parent, path).lstrip('/'))
                    for f in found:
                        directories.remove(f)
                        if desc == 'optional':
                            res['optionalDirs'].append(join(parent, f.basename).lstrip('/') + '/')
                        else:
                            res['requiredDirs'].append(join(parent, f.basename).lstrip('/') + '/')
                else:
                    found = []
                    for ent in directories:
                        if ent.basename == path:
                            if dirent is not None:
                                self._check(dirent, join(parent, path).lstrip('/'), res)
                            found.append(ent)
                            break
                    else:
                        if desc == 'required':
                            res['missingDirs'].append(join(parent, path).strip('/') + '/')
                    for f in found:
                        directories.remove(f)
                        if desc == 'optional':
                            res['optionalDirs'].append(join(parent, f.basename).lstrip('/') + '/')
                        else:
                            res['requiredDirs'].append(join(parent, f.basename).lstrip('/') + '/')
        for ent in files:
            res['unwantedFiles'].append(join(parent, ent.basename).lstrip('/'))
        for ent in directories:
            res['unwantedDirs'].append(join(parent, ent.basename).strip('/') + '/')
        return res

    def _compare_path_pattern(self, a, b):
        p1, _ = a
        p2, _ = b
        if p1[0] == p2[0] == '*':
            if '.' in p1:
                if '.' in p2:
                    return 0
                else:
                    return -1
            if '.' in p2:
                return 1
        if p1[0] == '*' and p2[0] != '*':
            return -1
        if p2[0] == '*' and p1[0] != '*':
            return 1
        return cmp(p1, p2)

