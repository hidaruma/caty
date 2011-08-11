# coding: utf-8
from caty.template.core.vm import Bytecode
from StringIO import StringIO
import caty
class BytecodeIOError(Exception):
    pass

class IBytecodeLoader(object):
    u"""バイトコードローダーインターフェース。
    バイトコードローダーは以下の機能に付いての責務を負うものとする。
    * 指定されたパスのデータをコンパイルし、メモリとファイルシステムに保存する
    * 指定されたパスに対応するバイトコードを呼出側に返す
    また、これらの処理を行うために _compiler, _io,  _persister の
    三つの属性（Compiler, ResourceIO, IBytecodePersister）を適切な形で初期化すること。
    """
    compiler = property(lambda self:self._compiler)
    io = property(lambda self:self._io)
    persister = property(lambda self:self._persister)

    def store(self, path):
        raise NotImplementedError

    def load(self, path):
        raise NotImplementedError

class IBytecodePersister(object):
    u"""バイトコードの読み書きインターフェース。
    """
    def read(self, fo):
        raise NotImplementedError

    def write(self, fo, bytecode_list):
        raise NotImplementedError


class TextBytecodePersister(IBytecodePersister):
    u"""テキスト形式でバイトコードを保存し、テキスト形式のバイトコードを読み出す。
    将来的にバイナリ形式でのバイトコードの保存も考えられるが、
    人間が手書きできるとなるとテキスト形式にせざるをえない。
    """
    version = '0.5'
    def write(self, fo, bytecode_list):
        tmp = StringIO()
        tmp.write('text: version %s\n' % self.version)
        for bc in bytecode_list:
            if isinstance(bc, tuple):
                line = '%d %s\n' % (bc[0], self.repr(bc[1]))
            elif isinstance(bc, Bytecode):
                line = '%d %s\n' % (bc.opcode, self.repr(bc.value))
            else:
                raise BytecodeIOError('Invalide data type: %s' % str(bc.__class__.__name__))
            tmp.write(line)
        tmp.seek(0)
        fo.write(tmp.read())

    def read(self, fo):
        bc_list = []
        lines = fo.read().splitlines()
        version = lines.pop(0)
        if 'text' not in version:
            raise BytecodeIOError('Unknown format or version: %s' % version)
        num = version.split(' ')[-1]
        if num != self.version: return None
        for line in lines:
            if ' ' in line:
                code, value = line.split(' ', 1)
            else:
                code = line
            bc_list.append(Bytecode(int(code), eval(value)))
        return tuple(bc_list)

    def repr(self, v):
        if v is caty.UNDEFINED:
            return 'caty.UNDEFINED'
        else:
            return repr(v)

class BytecodeLoader(IBytecodeLoader):
    u"""標準的なバイトコードローダー。
    コンパイル処理とリソースの取得処理はすべて移譲し、
    このクラスではタイムスタンプのチェック、キャッシュ処理などのコントロールを行う。
    """
    def __init__(self, compiler, io, persister):
        self._compiler = compiler
        self._io = io
        self._bytecode_chache = {}
        self._persister = persister
    
    def store(self, path):
        bytecode_path = path + '.ctpl'
        bc = self.compiler.compile(self.io.open(path))
        fo = self.io.open(bytecode_path, 'wb')
        try:
            self.persister.write(fo, bc)
        except:
            fo.close()
            self.io.delete(bytecode_path)
            raise
        else:
            fo.close()
        self._bytecode_chache[path] = bc
        return

    def _if_modified(self, path):
        orig_ts = self.io.last_modified(path)
        bc_ts = self.io.last_modified(path + '.ctpl')
        return orig_ts > bc_ts

    def _is_compiled(self, path):
        return self.io.exists(path + '.ctpl')

    def load(self, path):
        if not self._is_compiled(path) or self._if_modified(path):
            self.store(path)
        elif path not in self._bytecode_chache:
            fo = self.io.open(path + '.ctpl')
            c = self.persister.read(fo)
            fo.close()
            if c is not None:
                self._bytecode_chache[path] = c
            else:
                self.store(path)
        return self._bytecode_chache[path]

