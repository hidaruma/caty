#coding:utf-8
from caty.core.command import Command
from caty.core.exception import InternalException
class CommandLoader(object):
    def __init__(self, fs, global_command=None):
        self.command_dict = load_commands(fs)
        if global_command:
            self.command_dict.update(global_command.command_dict)
        self.builtin = BuiltinLoader()

    def get(self, pkg, cls):
        if pkg.startswith('caty.'):
            return self.builtin.get(pkg, cls)
        return self.command_dict[pkg][cls]

class BuiltinLoader(object):
    def get(self, pkg, cls):
        mod = __import__(pkg, fromlist=[cls])
        return getattr(mod, cls)

def load_commands(fs):
    d = {}
    for m in pseud_modules(fs):
        pkgname = m.name
        g_dict = {}
        module = dynamic_load(m, g_dict)
        d[pkgname] = module
    return d

def pseud_modules(fs):
    pms = []
    for e in fs.DirectoryObject('/').read(True):
        if e.path.endswith('.py'):
            pms.append(PseudoModule(e))
    return pms#dependency_sort(pms)

class Tree(object):
    u"""依存性のソートに用いる。
    ある PseudoModule を挿入するとき、それが root に依存していたら右へ、
    互いに依存していなかったら左へ、 root が依存してたら root と入れ替えて
    root を右へ追加という手順を踏む。
    """
    def __init__(self, v):
        self.root = v
        self.left = None
        self.right = None

    def insert(self, v):
        x = self.root.depends(v)
        y = v.depends(self.root)
        if x and y:
            raise InternalException(u'Cross reference has detected: $mod1, $mod2', mod1=x, mod2=y)
        elif x:
            t = Tree(v)
            t.add_right(self.root)
            return t
        elif y:
            self.add_right(v)
            return self
        else:
            self.add_left(v)
            return self

    def add_left(self, v):
        if self.left == None:
            self.left = v
        else:
            if not isinstance(self.left, Tree):
                self.left = Tree(self.left)
            self.left.insert(v)

    def add_right(self, v):
        if self.right == None:
            self.right = v
        else:
            if not isinstance(self.right, Tree):
                self.right = Tree(self.right)
            self.right.insert(v)

    def depends(self, v):
        return self.root.depends(v)

    @property
    def name(self):
        return self.root.name

    def to_list(self):
        return list(self.to_generator())

    def to_generator(self):
        if isinstance(self.left, Tree):
            for i in self.left.to_generator():
                yield i
        else:
            if self.left:
                yield self.left
        
        yield self.root

        if isinstance(self.right, Tree):
            for i in self.right.to_generator():
                yield i
        else:
            if self.right:
                yield self.right


def dependency_sort(pms):
    r = Tree(pms.pop(0))
    for a in pms:
        r = r.insert(a)
    return r.to_list()

import types
def dynamic_load(pm, g_dict):
    code = pm.code
    obj = compile(code, pm.path, 'exec')
    g_dict['__file__'] = pm.abspath
    exec obj in g_dict
    module = types.ModuleType(pm.name)
    module.__dict__.update(g_dict)
    g_dict[pm.name] = module
    g_dict.update(g_dict)
    d = {}
    for k, v in g_dict.iteritems():
        if isinstance(v, types.TypeType) and issubclass(v, Command):
            d[k] = v
    return d

import _ast
class PseudoModule(object):
    u"""擬似モジュールオブジェクト。
    Caty ではサイトごとの commands をサーチパスに置かないため、共通ライブラリが作れない状態になっている。
    そのため他の commands 配下のモジュールを参照している部分については

    * import, from を削除
    * インポートしているライブラリを exec 時グローバル辞書としてインジェクト

    という手順を経て処理する。
    """
    def __init__(self, fo):
        # 改行文字が LF でないと compile 不能なため
        self.raw_code = fo.read().replace('\r\n', '\n').replace('\r', '\n')
        if type(self.raw_code) == unicode:
            self.raw_code = self.raw_code.encode(self._find_encoding(self.raw_code))
        self.abspath = fo.real_path
        self.path = fo.path
        #self.ast = compile(self.raw_code, '', 'exec', _ast.PyCF_ONLY_AST)
        path = fo.path[1:]
        if path.endswith('/__init__.py'):
            path = path.replace('/__init__.py', '.py')
        self.name = str(path.replace('/', '.')[:-3])
        #self.rds, self.imports = self.generate_deletor_and_find_import(self.ast)
        #self.dependency_list = set()
        
    def depends(self, another):
        u"""引数のモジュールに依存しているかどうか。
        依存していた場合、依存性リストに追加する。
        """
        if another.name in self.imports:
            self.dependency_list.add(another.name)
            return True
        return False

    def generate_deletor_and_find_import(self, ast):
        rds = {}
        imports = []
        for i in find_import(ast):
            from_name, import_name, as_name, start, end, offset = i
            imports.append(from_name if from_name != '' else import_name)
            rds[imports[-1]] = RangeDeletor(start, end, offset)
        return rds, imports

    @property
    def code(self):
        #code = self.raw_code.splitlines(True)
        #for rd in [x for n, x in self.rds.items() if n in self.dependency_list]:
        #    rd.delete_import(code)
        #r = ''.join(code)
        # もしかしたら必要になるかも
        return self.raw_code

    def _find_encoding(self, text):
        import re
        line = text.splitlines()[0]
        c = re.compile('coding *: *(.+)')
        m = c.search(line)
        if m:
            return m.group(1)
        return 'utf-8'

    def __str__(self):
        return self.path

class RangeDeletor(object):
    def __init__(self, start, end, offset):
        self.start = start
        self.end = end
        self.offset = offset

    def delete_import(self, seq):
        if self.start == self.end:
            seq[self.start-1] = self.deleted
        else:
            for i in range(self.start - 1, self.end - 1):
                seq[i] = self.deleted
    
    @property
    def deleted(self):
        return ' ' * self.offset + 'pass\n'


def find_import(ast):
    x = PeekableIterator(ast.body)
    for b in x:
        if hasattr(b, 'body'):
            for i in find_import(b):
                yield i
        if isinstance(b, _ast.Import):
            for n in b.names:
                if n.asname:
                    yield ('', n.name, n.asname, b.lineno, b.lineno, b.col_offset)
                else:
                    yield ('', n.name, n.name, b.lineno, b.lineno, b.col_offset)
        elif isinstance(b, _ast.ImportFrom):
            for n in b.names:
                if n.asname:
                    yield (b.module, n.name, n.asname, b.lineno, x.peek().lineno, b.col_offset)
                else:
                    yield (b.module, n.name, n.name, b.lineno, x.peek().lineno, b.col_offset)

class PeekableIterator(object):
    def __init__(self, it):
        self.iter = list(it)
        self.index = -1
        self.end = len(self.iter)

    def __iter__(self):
        return self

    def next(self):
        self.index += 1
        if self.index == self.end:
            raise StopIteration()
        return self.iter[self.index]

    def peek(self):
        if self.index < self.end - 1:
            return self.iter[self.index + 1]
        else:
            return self.iter[self.index]

