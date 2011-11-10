#coding: utf-8
name = u'gen'
schema = u"""
/**
 * 与えられた型名から値を自動生成する。
 */
command sample {
    @[default("var")] "occur":("var"|"once"|"min")?, 
    @[default("rand")]"string": ("rand"|"empty"|"implied")?
  } [string typename] :: void -> any
  reads schema
  refers python:caty.core.std.command.gen.Sample;

/**
 * 与えられたパスパターンからURLを生成する。
 */
command url [PathPattern pathPattern] :: void -> string
    throws BadArg
    reads env
    refers python:caty.core.std.command.gen.Url;


"""
