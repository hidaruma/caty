# coding: utf-8
from caty.core.command import Builtin

name = 'list'
schema =''

class Zip(Builtin):
    command_decl = u"""
    /**
     * 二つのリストを入力として受け取り、それらの各要素をタプルにしたもののリストを返す。
     * 例えば [1,2,3] と ["a", "b", "c"] というデータに対しては、 [[1, "a"], [2, "b"], [3, "c"]] というデータを返す。
     *
     * このコマンドは unzip と対になっている。
     */
    command zip<S, T> :: [[S*], [T*]] -> [[S, T]*]
            refers python:caty.command.listlib.Zip;
    """
    def execute(self, input):
        return map(list, zip(input[0], input[1]))

class Zip3(Builtin):
    command_decl = u"""
    /**
     * zipと同様な機能を持つが、三のリストを入力として受け取る。
     * 例えば [1,2,3], ["a", "b", "c"], ["x", "y", "z"] というデータに対しては、 
     * [[1, "a", "x"], [2, "b", "y"], [3, "c", "z"]] というデータを返す。
     *
     * このコマンドは unzip3 と対になっている。
     */
    command zip3<S, T, U> :: [[S*],[T*],[U*]] -> [[S, T, U]*]
            refers python:caty.command.listlib.Zip3;
    """
    def execute(self, input):
        return map(list, zip(input[0], input[1], input[2]))

class UnZip(Builtin):
    command_decl = u"""
        /**
         * 2要素のタプルのリストを受け取り、それらを二つのリストのタプルにして返す。
         * 例えば [[1, "a"], [2, "b"], [3, "c"]] というデータに対しては、 [1,2,3] と ["a", "b", "c"] というデータを返す。
         * 
         * このコマンドは zip コマンドと対になっている。
         */
        command unzip<S, T> :: [[S, T]*] -> [[S*], [T*]]
            refers python:caty.command.listlib.UnZip;
    """
    def execute(self, input):
        r1 = []
        r2 = []
        for x, y in input:
            r1.append(x)
            r2.append(y)
        return [r1, r2]

class UnZip3(Builtin):
    command_decl = u"""
        /**
         * 3要素のタプルのリストを受け取り、それらを三つのリストのタプルにして返す。
         * 例えば [[1, "a", "x"], [2, "b", "y"], [3, "c", "z"]] というデータに対しては、 
         * [1,2,3], ["a", "b", "c"], ["z", "y", "z"] というデータを返す。
         * 
         * このコマンドは zip3 コマンドと対になっている。
         */
        command unzip3 :: [[S, T, U]*] -> [[S*],[T*],[U*]] 
            refers python:caty.command.listlib.UnZip3;
    """
    def execute(self, input):
        r1 = []
        r2 = []
        r3 = []
        for x, y, z in input:
            r1.append(x)
            r2.append(y)
            r3.append(z)
        return [r1, r2, r3]

class Length(Builtin):
    command_decl = u"""
        /**
         * 入力値の長さを返す。
         */
        command length<S> :: [S*] -> integer
            refers python:caty.command.listlib.Length;
    """
    def execute(self, input):
        return len(input)

class Cycle(Builtin):
    command_decl = u"""
        /**
         * 引数が与えられた場合、入力値を引数の回数分だけ繰り返したリストを返す。
         * そうでない場合、第二入力値の回数分だけ第一入力値を繰り返したリストを返す。
         */
        command cycle<T> [integer] :: T -> [T*]
                :: [T, integer] -> [T*]
            refers python:caty.command.listlib.Cycle;
    """
    def setup(self, times=None):
        self.times = times

    def execute(self, input):
        times = self.times

        if times is None:
            times = input[1]
            src = input[0]
        else:
            src = input
        return [src for i in range(times)]

class Enumerate(Builtin):
    command_decl = u"""
        /**
         * 入力値を添字のリストと zip した値を返す。
         * 例えば ["x", "y", "z"] という入力に対しては [(0, "x"), (1, "y"), (2, "z")] という値が返る。
         */
        command enumerate<T> :: [T*] -> [[integer, T]*]
            refers python:caty.command.listlib.Enumerate;
    """
    def execute(self, input):
        r = []
        for a, b in enumerate(input):
            r.append([a, b])
        return r

class Sort(Builtin):
    command_decl = u"""
        /**
         * 入力値をソートして返す。
         * オプションの key が指定されて尚且つ入力値が object の配列の場合、
         * key にあたるプロパティがソートキーとして使われる（JSON パス式には未対応）。
         */
        command sort<T> {"key":string?, "reverse": boolean?} :: [T*] -> [T*]
            refers python:caty.command.listlib.Sort;
    """
    
    def setup(self, opts):
        self.key = opts.key
        self.rev = opts.reverse or False

    def execute(self, input):
        r = input[:]
        if self.key:
            r.sort(key=lambda a:a[self.key], reverse=self.rev)
        else:
            r.sort(reverse=self.rev)
        return r

class Slice(Builtin):
    command_decl = u"""
        /**
         * 入力値のスライスを返す。
         * 第一引数は開始インデックスで、第二引数は終了インデックスとなる。
         * 第二引数は省略可能で、その場合は配列の最終要素までのスライスが返される。
         */
        command slice<T> [integer, integer] :: [T*] -> [T*]
                      [integer] :: [T*] -> [T*]
            refers python:caty.command.listlib.Slice;
    """
    def setup(self, start, end=None):
        self.start = start
        self.end = end

    def execute(self, input):
        if self.end:
            return input[self.start:self.end]
        else:
            return input[self.start:]


class Concat(Builtin):
    command_decl = u"""
    /**
     * 二つの配列を結合した新しい配列を返す。
     */
    command concat :: [[any*], [any*]] -> [any*]
        refers python:caty.command.listlib.Concat;
    """
    def execute(self, input):
        return input[0] + input[1]

from caty.jsontools import tagged
class Contains(Builtin):
    command_decl = u"""
    /**
     * 入力値の第一要素が、第二要素を含むかどうか返す。
     */
    command contains :: [[any*], any] -> @Contains boolean | @Not boolean
        refers python:caty.command.listlib.Contains;
    """
    def execute(self, input):
        v = input[1] in input[0]
        return tagged(u'Contains' if v else u'Not', v)



