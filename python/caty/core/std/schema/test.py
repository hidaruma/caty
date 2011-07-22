#coding: utf-8

name = 'test'
schema = u"""
@[test] command list-testfiles [string] :: void -> [string*]
reads testfiles
refers python:caty.core.std.command.test.ListTestFiles;


@[test] command read-test [string] :: void -> string
reads testfiles
refers python:caty.core.std.command.test.ReadTestFile;


@[test] command pp :: any -> string
refers python:caty.core.std.command.test.PP;

@[test] command write-file [string] :: string -> void
updates testfiles
refers python:caty.core.std.command.test.WriteFile;
"""
