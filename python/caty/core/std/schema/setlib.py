#coding: utf-8

name = 'set'
schema = u"""
/**
 * 二つの配列a, bを入力に取り、それらを集合として扱い、bに含まれていないaの要素を返す。
 */
command diff :: [array a, array b] -> array
    refers python:caty.core.std.command.setlib.Diff;

"""
