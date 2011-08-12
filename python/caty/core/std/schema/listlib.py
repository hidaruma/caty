#coding: utf-8

name = 'list'
schema = u"""
/**
 * 二つのリストを入力として受け取り、それらの各要素をタプルにしたもののリストを返す。
 * 例えば [1,2,3] と ["a", "b", "c"] というデータに対しては、 [[1, "a"], [2, "b"], [3, "c"]] というデータを返す。
 *
 * このコマンドは unzip と対になっている。
 */
command zip<S, T> :: [[S*], [T*]] -> [[S, T]*]
        refers python:caty.core.std.command.listlib.Zip;

/**
 * zipと同様な機能を持つが、三のリストを入力として受け取る。
 * 例えば [1,2,3], ["a", "b", "c"], ["x", "y", "z"] というデータに対しては、 
 * [[1, "a", "x"], [2, "b", "y"], [3, "c", "z"]] というデータを返す。
 *
 * このコマンドは unzip3 と対になっている。
 */
command zip3<S, T, U> :: [[S*],[T*],[U*]] -> [[S, T, U]*]
        refers python:caty.core.std.command.listlib.Zip3;

/**
 * 2要素のタプルのリストを受け取り、それらを二つのリストのタプルにして返す。
 * 例えば [[1, "a"], [2, "b"], [3, "c"]] というデータに対しては、 [1,2,3] と ["a", "b", "c"] というデータを返す。
 * 
 * このコマンドは zip コマンドと対になっている。
 */
command unzip<S, T> :: [[S, T]*] -> [[S*], [T*]]
    refers python:caty.core.std.command.listlib.UnZip;

/**
 * 3要素のタプルのリストを受け取り、それらを三つのリストのタプルにして返す。
 * 例えば [[1, "a", "x"], [2, "b", "y"], [3, "c", "z"]] というデータに対しては、 
 * [1,2,3], ["a", "b", "c"], ["z", "y", "z"] というデータを返す。
 * 
 * このコマンドは zip3 コマンドと対になっている。
 */
command unzip3 :: [[S, T, U]*] -> [[S*],[T*],[U*]] 
    refers python:caty.core.std.command.listlib.UnZip3;

/**
 * 入力値の長さを返す。
 */
command length<S> :: [S*] -> integer
    refers python:caty.core.std.command.listlib.Length;

/**
 * 引数が与えられた場合、入力値を引数の回数分だけ繰り返したリストを返す。
 * そうでない場合、第二入力値の回数分だけ第一入力値を繰り返したリストを返す。
 */
command cycle<T> [integer] :: T -> [T*]
        :: [T, integer] -> [T*]
    refers python:caty.core.std.command.listlib.Cycle;

/**
 * 入力値を添字のリストと zip した値を返す。
 * 例えば ["x", "y", "z"] という入力に対しては [(0, "x"), (1, "y"), (2, "z")] という値が返る。
 */
command enumerate<T> :: [T*] -> [[integer, T]*]
    refers python:caty.core.std.command.listlib.Enumerate;

/**
 * 入力値をソートして返す。
 * オプションの key が指定されて尚且つ入力値が object の配列の場合、
 * key にあたるプロパティがソートキーとして使われる（JSON パス式には未対応）。
 */
command sort<T> {"key":string?, "reverse": boolean?} :: [T*] -> [T*]
    refers python:caty.core.std.command.listlib.Sort;

/**
 * 入力値のスライスを返す。
 * 第一引数は開始インデックスで、第二引数は終了インデックスとなる。
 * 第二引数は省略可能で、その場合は配列の最終要素までのスライスが返される。
 */
command slice<T> [integer, integer] :: [T*] -> [T*]
              [integer] :: [T*] -> [T*]
    refers python:caty.core.std.command.listlib.Slice;

/**
 * 二つの配列を結合した新しい配列を返す。
 */
command concat :: [[any*], [any*]] -> [any*]
    refers python:caty.core.std.command.listlib.Concat;

/**
 * 入力値の第一要素が、第二要素を含むかどうか返す。
 */
command contains :: [[any*], any] -> @Contains boolean | @Not boolean
    refers python:caty.core.std.command.listlib.Contains;

/**
 * ルーズ配列(undefinedを含んだ配列)をundefinedを含まない配列にして返す。
 */
command tighten :: [any*] -> [any*]
    refers python:caty.core.std.command.listlib.Tighten;

/**
 * 連続する整数値からなる配列を返す。
 */
command range [integer start, integer end] :: void  -> [integer*]
    refers python:caty.core.std.command.listlib.Range;

"""

