# coding: utf-8
import types
from StringIO import StringIO

from caty.util import error_to_ustr
from caty.template.core.instructions import *
from caty.template.core.filter import get_filters, AbstractFilter, FilterContainer
from caty.template.core.context import *
from caty.template.core.renderer import *
from caty.template.core.exceptions import *
import caty.core.runtimeobject as ro
import caty.jsontools as json
import caty.core.schema as schema

class RawStringFilter(AbstractFilter):
    name = 'noescape'
    def filter(self, s):
        if isinstance(s, VariableString):
            return RawString(s.string)
        else:
            return RawString(s if isinstance(s, basestring) else str(s))

class BytecodeIterator(object):
    u"""バイトコード用のコンテナクラス。
    イテレータのように使用可能だが、ジャンプ命令に対応するためにランダムアクセス可能とする。
    あくまでもイテレータなので、要素への変更は行わない事を前提とする。
    最適化やマクロによるバイトコード変換時には、新たにイテレータを再生成すること。
    """
    def __init__(self, iterable):
        u"""任意のイテレート可能オブジェクトを引数とする。
        """
        self.iterable = tuple(iterable)
        self.cursor = 0
        self.last = len(self.iterable)

    def next(self):
        if self.last - 1 <= self.cursor:
            raise StopIteration
        r = self.iterable[self.cursor]
        self.cursor += 1
        return r

    def back(self):
        self.cursor -= 1

    index = property(lambda self:self.cursor)

    def jump_to(self, index):
        u"""指定されたインデックスにイテレータの現在位置を設定する。
        """
        self.cursor = index
        if self.cursor < -1:
            self.cursor = -1

    def _current(self):
        return self.iterable[self.cursor]
    current = property(_current)

    def __str__(self):
        r = []
        for n, i in enumerate(self.iterable):
            if n != self.cursor:
                r.append('   %s' % str(i))
            else:
                r.append('-> %s' % str(i))
        return '\n'.join(r)

import caty
UNDEF = caty.UNDEFINED

class Bytecode(object):
    u"""バイトコードオブジェクト。
    別にタプルでも良いのだが、可読性のためにこちらを採用。
    """
    def __init__(self, opcode, value=''):
        self.opcode = opcode
        self.value = value

    def __str__(self):
        return ('%s %s' % (repr(get_name(self.opcode)), repr(self.value)))

class Stack(object):
    u"""リストベースのスタック。
    リストをそのまま使ってもよいが、 append/pop よりも
    push/pop/top/ のようなインターフェースの方が
    スタックマシンを操作するときのメンタルモデルに近い。
    """
    def __init__(self):
        self.list = []

    def push(self, v):
        self.list.append(v)

    def pop(self):
        try:
            r = self.list.pop(-1)
            return r
        except IndexError:
            raise TemplateRuntimeError(ro.i18n.get(u'Stack is empty'))

    def top(self):
        return self.list[-1]

    def is_empty(self):
        return len(self.list) == 0

    def __repr__(self):
        return repr(self.list)

class VirtualMachine(object):
    u"""バイトコードを解釈し、出力ストリームに書き出す仮想マシン。
    あくまでも処理の対象はバイトコードであり、
    ファイル/ストリームからバイトコードを読み出したりコンパイルしたりという作業は別クラスへ委譲する。
    """
    def __init__(self, bytecode_loader, schema_module):
        self._context = Context({})
        self._filters = FilterContainer()
        self._filters.add(RawStringFilter())
        for f in get_filters():
            self._filters.add(f)
        self._macro = {}
        self._functions = {}
        self._func_match = {}
        self._groups = {}
        self._out = StringIO()
        self._bytecode_loader = bytecode_loader
        self._include_callback = None
        self._filter_executor = None
        self._renderer = HTMLRenderer()
        self._masked_context = []
        self.allow_undef = False
        self.schema_module = schema_module

    def filters():
        def get(self):
            return self._filter

        def set(self, value):
            self._filter = value
        return get, set
    filters = property(*filters())

    def context():
        def get(self):
            return self._context

        def set(self, value):
            if isinstance(value, dict):
                self._context = Context(value)
            else:
                self._context = value

        return get, set
    context = property(*context())

    def renderer():
        def get(self):
            return self._renderer
        def set(self, value):
            self._renderer = value
        return get, set
    renderer = property(*renderer())

    def dup(self):
        new_vm = VirtualMachine(self._bytecode_loader, self.schema_module)
        new_vm._context = self._context
        new_vm._filters = self._filters
        new_vm._out = self._out
        return new_vm

    def _evaluate(self, bi):
        u"""バイトコードの実行関数。
        バイトコードのリストを受け取り、
        実行した結果をジェネレータとして返す。
        """
        stack = Stack()
        labelmap = {}
        opmap = {}
        filters = self._filters
        def load(k):
            try:
                v = self.context.get(k)
            except Exception, e:
                if self.allow_undef:
                    v = DummyContext(k)
                else:
                    raise
            stack.push(v)
            return
        opmap[LOAD] = load
        
        def push(v):
            stack.push(v)
            return
        opmap[PUSH] = push

        def pop(ignore):
            s = stack.pop()
            if isinstance(s, RawString):
                return s
            elif isinstance(s, basestring):
                return VariableString(s)
            else:
                return s
        opmap[POP] = pop

        def label(name):
            labelmap[name] = bi.index
            return
        opmap[LABEL] = label

        def jmp(l):
            index = labelmap.get(l, -1)
            if index == -1:
                while bi.current:
                    code = bi.current.opcode
                    value = bi.current.value
                    if code == LABEL and value == l:
                        label(l)
                        break
                    bi.next()
                else:
                    raise TemplateRuntimeError(ro.i18n.get(u'Undefined label: $label', label=l))
            else:
                bi.jump_to(index)
            return
        opmap[JMP] = jmp

        def jmpunless(l):
            if not stack.pop():
                jmp(l)
            return
        opmap[JMPUNLESS] = jmpunless

        def newctx(ignore):
            self.context.new({})
            return
        opmap[NEWCTX] = newctx

        def delctx(ignore):
            self.context.delete()
        opmap[DELCTX] = delctx

        def cpush(k):
            self.context[k] = stack.pop()
            return
        opmap[CPUSH] = cpush

        def macro(name):
            if name in self._macro:
                return
            i = bi.index
            while bi.current:
                if bi.current.opcode == RETURN:
                    break
                bi.next()
            else:
                raise TemplateRuntimeError('Missing end of macro definition: %s' % name)
            self._macro[name] = i
        opmap[MACRO] = macro
        
        def ret(ignore):
            bi.jump_to(stack.pop())
            return
        opmap[RETURN] = ret

        def expand(name):
            macro_index = self._macro.get(name, None)
            if not macro_index:
                raise TemplateRuntimeError('Macro definition not found: %s' % name)
            push(bi.index)
            bi.jump_to(macro_index)
            return
        opmap[EXPAND] = expand

        def string(value):
            return RawString(value)
        opmap[STRING] = string

        def defined(key):
            if UNDEF == self.context.get(key, UNDEF):
                print 'Template Warning: Undefined Variable', key
                stack.push(False)
            else:
                stack.push(True)
        opmap[DEFINED] = defined

        def call(args):
            if isinstance(args, list):
                name, argc = args
            else:
                name = args
                argc = 1
            argc = int(argc)
            argv = []
            for i in range(argc):
                argv.append(stack.pop())
            argv = list(reversed(argv))
            if self._filter_executor is None:
                f = filters.get(name)
                if f == None:
                    raise TemplateRuntimeError(ro.i18n.get(u'Undefined $object: $value', object=u'filter', value=name))
                push(f(*argv))
            else:
                v = self._filter_executor(name, argv)
                push(v)
            return
        opmap[CALL] = call
        
        def include(name):
            if self._include_callback == None:
                newvm = self.dup()
                newcode = self._bytecode_loader.load(name)
                newvm.context.new(stack.pop())
                newvm.write(newcode, self._out)
                newvm.context.delete()
            else:
                self._out.write(self._include_callback(name, stack.pop()))
            return
        opmap[INCLUDE] = include

        def negate(ignore):
            stack.push(not stack.pop())
            return
        opmap[NOT] = negate

        def add(ignore):
            stack.push(stack.pop() + stack.pop())
            return
        opmap[ADD] = add

        def eq(ignore):
            stack.push(stack.pop() == stack.pop())
            return
        opmap[EQ] = eq

        def lt(ignore):
            a = stack.pop()
            b = stack.pop()
            stack.push(a < b)
            return
        opmap[LT] = eq

        def le(ignore):
            a = stack.pop()
            b = stack.pop()
            stack.push(a <= b)
            return
        opmap[LE] = le
        
        def length(ignore):
            v = stack.pop()
            if isinstance(v, DummyContext):
                v= []
            stack.push(len(v))
            return
        opmap[LEN] = length

        def at(ignore):
            p = bi.cursor
            i = stack.pop()
            ls = stack.pop()
            if isinstance(ls, DummyContext):
                v = str(ls) + ('[%d]' % i)
            else:
                v = ls[i]
            stack.push(v)
            return 
        opmap[AT] = at

        def ref(ignore):
            stack.push(context.dict)
            return
        opmap[REFCONTEXT] = ref

        def item(key):
            d = stack.pop()
            if isinstance(d, DummyContext):
                v = str(d) + '.' + key
            else:
                v = d[key]
            stack.push(v)
            return
        opmap[ITEM] = item

        def enum(ignore):
            v = stack.pop()
            if isinstance(v, basestring):
                raise TemplateRuntimeError('String is not iterable: %s' % v)
            stack.push(list(enumerate(v) if not isinstance(v, dict) else v.items()))
            return
        opmap[ENUM] = enum

        def cdel(k):
            del self.context[k]
            return
        opmap[CDEL] = cdel

        def subcontext(k):
            if k == '':
                stack.push(self.context)
            else:
                stack.push(self.context.get(k))
        opmap[SUBCONTEXT] = subcontext

        def mask_context(ignore):
            self._masked_context.append(self._context)
            value = stack.pop()
            if isinstance(value, dict):
                _context = {}
                _context['_CONTEXT'] = value
                _context['CONTEXT'] = value
                _context.update(value)
            else:
                _context = {'_CONTEXT': value}
                _context['CONTEXT'] = value
            self._context = Context(_context, False)
        opmap[MASK_CONTEXT] = mask_context

        def unmask_context(ignore):
            self._context = self._masked_context.pop(-1)
        opmap[UNMASK_CONTEXT] = unmask_context

        def discard(ignore):
            stack.pop()
        opmap[DISCARD] = discard

        def def_function(name):
            if name in self._functions:
                return
            i = bi.index
            while bi.current:
                if bi.current.opcode == RETURN:
                    break
                bi.next()
            else:
                raise TemplateRuntimeError('Missing end of function definition: %s' % name)
            self._functions[name] = i
        opmap[FUNCTION_DEF] = def_function

        def call_template(name):
            tpl_index = self._functions.get(name, None)
            if not tpl_index:
                raise TemplateRuntimeError('Function definition not found: %s' % name)
            # 引数と戻り先アドレスのスタック位置を交換
            a = stack.pop()
            stack.push(bi.index)
            stack.push(a)
            bi.jump_to(tpl_index)
            return
        opmap[CALL_TEMPLATE] = call_template

        def def_match(namespace):
            i = bi.index
            if namespace in self._func_match:
               if i in self._func_match[namespace]:
                   return
               else:
                   self._func_match[namespace].append(i)
            else:
                self._func_match[namespace] = [i]
            while bi.current:
                if bi.current.opcode == FUNCTION_DEF:
                    bi.back()
                    break
                bi.next()
            else:
                raise TemplateRuntimeError('Missing end of function definition: %s' % name)
        opmap[FUNCTION_MATCH] = def_match

        def validate(type_name):
            try:
                scm = self.schema_module[type_name]
            except:
                raise TemplateRuntimeError('Unkown type: %s' % type_name)
            scm.validate(stack.top())
            stack.push(type_name)
                
        opmap[VALIDATE] = validate

        def dispatch(tag_name):
            t, v = json.split_tag(stack.top())
            if tag_name == '*':
                stack.list[-1] = v
                stack.push(t)
                stack.push(True)
            elif tag_name == '*!':
                if t in schema.type:
                    stack.push(t)
                    stack.push(False)
                else:
                    stack.push(t)
                    stack.push(True)
            else:
                for name in map(lambda s: s.strip(), tag_name.split('|')):
                    if t == name:
                        stack.list[-1] = v
                        stack.push(t)
                        stack.push(True)
                        break
                else:
                    stack.push(t)
                    stack.push(False)
            return
        opmap[DISPATCH] = dispatch

        def def_group(name):
            if name in self._groups:
                return
            i = bi.index
            self._groups[name] = i
        opmap[GROUP_DEF] = def_group

        def call_group(name):
            tpl_index = self._func_match.get(name, None)
            if not tpl_index:
                raise TemplateRuntimeError('Group definition not found: %s' % name)
            # 引数と戻り先アドレスのスタック位置を交換
            a = stack.pop()
            stack.push(bi.index)
            stack.push(a)
            bi.jump_to(tpl_index[0])
            return
        opmap[CALL_GROUP] = call_group

        def nop(*args):
            if not stack.is_empty():
                bi.jump_to(stack.pop())
            return
        opmap[END_GROUP] = nop

        def swap(ignore):
            v1 = stack.pop()
            v2 = stack.pop()
            stack.push(v1)
            stack.push(v2)
            return
        opmap[SWAP] = swap

        while bi.current:
            code = bi.current.opcode
            value = bi.current.value
            operation = opmap.get(code, None)
            if not operation:
                raise TemplateRuntimeError(ro.i18n.get(u'Undefined operation: $code', code=code))
            r = operation(value)
            if r != None:
                if isinstance(r, types.GeneratorType):
                    for ri in r:
                        yield r
                else:
                    yield r
            bi.next()
    
    def write(self, bytecode, out):
        if not isinstance(bytecode, BytecodeIterator) and isinstance(bytecode[0], Bytecode):
            bi = BytecodeIterator(bytecode)
        elif not isinstance(bytecode[0], Bytecode):
            bi = BytecodeIterator([Bytecode(*b) for b in bytecode])
        else:
            bi = bytecode
        try:
            self._out = out
            for r in self._evaluate(bi):
                out.write(self._renderer.render(r))
        except Exception, e:
            import traceback
            traceback.print_exc()
            out.seek(0)
            c = out.read().decode('utf-8')
            raise TemplateRuntimeError( u'%s\n%s\n%s' % (c, bi, error_to_ustr(e)))

