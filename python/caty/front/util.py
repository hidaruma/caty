# coding: utf-8
from optparse import OptionParser
from caty.util import init_writer, debug
from caty.util.optionparser import OptionParser
import locale
def _get_encoding():
    try:
        l = locale.getpreferredencoding()
        try:
            ''.decode(l)
            return l
        except Exception, e:
            init_writer('utf-8')
            debug.write(e)
            return 'utf-8'
    except Exception, e:
        init_writer('utf-8')
        debug.write(e)
        return 'utf-8'

def make_base_opt_parser(mode):
    parser = OptionParser(usage='usage: python stdcaty.py %s [OPTIONS]' % mode)
    parser.add_option('-q', '--quiet', dest='quiet', default=False, action='store_true', help=u'起動メッセージを出力しない')
    parser.add_option('-s', '--system-encoding', dest='system_encoding', default=_get_encoding(), help=u'システムのエンコーディングを指定する')
    parser.add_option('-a', '--app', dest='apps', metavar='APP', action='append', default=[], help=u'APPを起動後のデフォルトアプリケーションにする\n複数指定された場合、最初のものがデフォルトに使われる')
    parser.add_option('--force-app', dest='force_app', metavar='APP', help=u'APPを_manifest.xjsonの記述に関わらず強制的に起動する')
    parser.add_option('-d', '--debug',action='store_true', help=u'デバッグモードで起動する')
    parser.add_option('--goodbye', help=u'起動直後に終了する')
    parser.add_option('--no-ambient', dest='no_ambient', action='store_true', help=u'スキーマやアクションを読み込まずに起動する')
    parser.add_option('--no-app', dest='no_app', action='store_true', help=u'起動時に--appで指定されたなかったアプリケーションを読み込まない\n--appが未指定の場合、rootだけが読み込まれる')
    return parser
