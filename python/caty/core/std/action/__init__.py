#coding: utf-8
from caty.core.action.entry import ResourceActionEntry
from caty.core.action.resource import DefaultResource
from caty.core.script.parser import ScriptParser
from caty.core.schema.base import Annotations

def create_default_resources(facility):
    yield DefaultResource('**.cgi|**.act|**.do', _script_actions(facility), u'system', u'script', u'スクリプト', Annotations([]))
    yield DefaultResource('**/|/', _dir_actions(facility), u'system', u'directory', u'ディレクトリ', Annotations([]))
    yield DefaultResource('**.*', _file_actions(facility), u'system', u'file', u'ファイル', Annotations([]))
    yield DefaultResource('**.html|**.xhtml|**.xml|**.htm', _template_actions(facility), u'system', u'html', u'テンプレート', Annotations([]))

def _script_actions(facility):
    parser = ScriptParser(facility)
    return {
        '/GET': ResourceActionEntry(parser.parse(u'call %0'), u'call %0', u'get'),
        '/POST': ResourceActionEntry(parser.parse(u'call %0'), u'call %0', u'post'),
        '/PUT': ResourceActionEntry(parser.parse(u'http:not-allowed %0 PUT'), u'http:not-allowed %0 PUT', u'put'),
        '/DELETE': ResourceActionEntry(parser.parse(u'http:not-allowed %0 PUT'), u'http:not-allowed %0 DELETE', u'delete'),
    }

def _dir_actions(facility):
    parser = ScriptParser(facility)
    return {
        '/GET': ResourceActionEntry(parser.parse(u'dir-index %0 GET'), u'dir-index %0 GET', u'get'),
    }

def _file_actions(facility):
    parser = ScriptParser(facility)
    return {
        '/GET': ResourceActionEntry(parser.parse(u'print --raw %0'), u'print --raw %0', u'get'),
    }

def _template_actions(facility):
    parser = ScriptParser(facility)
    return {
        '/GET': ResourceActionEntry(parser.parse(u'print %0'), u'print %0', u'get'),
    }



