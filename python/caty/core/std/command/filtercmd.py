#coding: utf-8
name = u'filter'
schema = u''
from caty.core.command import Builtin
import caty

class NotNullFilter(Builtin):
    command_decl = u"""
    /**
     * 入力値がnullまたは未定義でなければtrue, nullであればfalseを返す。
     *
     */
    @[filter]
    command notnull :: any -> boolean
        refers python:caty.command.filtercmd.NotNullFilter;
    """

    def execute(self, a):
        return a != None and a != caty.UNDEFINED

class NotEmptyFilter(Builtin):
    command_decl = u"""
    /**
     * 入力値が空文字、空リスト、空オブジェクト、null、未定義値でなければtrue, そうであればfalseを返す。
     *
     */
    @[filter]
    command notempty :: any -> boolean
        refers python:caty.command.filtercmd.NotEmptyFilter;
    """
    def execute(self, a):
        return a != [] and a != {} and a != '' and a != None and a != caty.UNDEFINED

class EmptyFilter(Builtin):
    command_decl = u"""
    /**
     * 入力値が空文字、空リスト、空オブジェクト、null、未定義値でなければfalse, そうであればtrueを返す。
     *
     */
    @[filter]
    command empty :: any -> boolean
        refers python:caty.command.filtercmd.EmptyFilter;
    """
    def execute(self, a):
        return a == [] or a == {} or a == '' or a == None or a == caty.UNDEFINED

class ModuloFilter(Builtin):
    command_decl = u"""
    /**
     * 入力値を引数で割ったその余りを返す。
     */
    @[filter]
    command mod [string] :: any -> any
        refers python:caty.command.filtercmd.ModuloFilter;
    """
    def setup(self, mod):
        self.mod = mod

    def execute(self, a):
        return a % a.__class__(self.mod)

class EqFilter(Builtin):
    command_decl = u"""
    /**
     * 入力値と引数が等しいかを返す。
     */
    @[filter]
    command eq [string] :: any -> boolean
        refers python:caty.command.filtercmd.EqFilter;
    """

    def setup(self, arg):
        self.arg = arg

    def execute(self, a):
        return a == self.arg

class NotEqFilter(Builtin):
    command_decl = u"""
    /**
     * 入力値と引数が異なっているかを返す。
     */
    @[filter]
    command ne [string] :: any -> boolean
        refers python:caty.command.filtercmd.NotEqFilter;
    """
    def setup(self, arg):
        self.arg = arg

    def execute(self, a):
        return a != self.arg

class NotFilter(Builtin):
    command_decl = u"""
    /**
     * 入力値の否定を返す。
     */
    @[filter]
    command not :: any -> boolean
        refers python:caty.command.filtercmd.NotFilter;
    """
    def execute(self, b):
        return not b

import caty
class DefinedFilter(Builtin):
    command_decl = u"""
    /**
     * 入力が未定義値でなければtrueを返す。
     */
    @[filter]
    command defined :: any -> boolean
        refers python:caty.command.filtercmd.DefinedFilter;
    """
    def execute(self, i):
        return i is not caty.UNDEFINED

class RawStringFilter(Builtin):
    command_decl = u"""
    /**
     * 文字列をエスケープしないようにテンプレートエンジンに伝える。
     */
    @[filter]
    command noescape :: any -> any
        refers python:caty.command.filtercmd.RawStringFilter;
    """
    def execute(self, s):
        from caty.template.core.context import VariableString, RawString
        if isinstance(s, VariableString):
            return RawString(s.string)
        else:
            return RawString(s if isinstance(s, basestring) else str(s))

class IsObject(Builtin):
    command_decl = u"""
    /**
     * 入力がオブジェクト型かどうかを判定する。
     */
    @[filter]
    command isobject :: any -> boolean;
    """
    def execute(self, input):
        input_type = type(input)
        if input_type == DictType:
            return true
        else:
            return false

class IsArray(Builtin):
    command_decl = u"""
    /**
     * 入力が配列型かどうかを判定する。
     */
    @[filter]
    command isarray :: any -> boolean;
    """
    def execute(self, input):
        input_type = type(input)
        if input_type == ListType:
            return true
        else:
            return false

