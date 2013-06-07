# coding: utf-8

__version__ = u'pp-2.0.0'
DEBUG = False


from caty.core.spectypes import * #XXX:互換性のため。後で直す。
from caty.core.spectypes import _Undefined
import sys
from caty.front import console, web, profiler
from caty.util import OptPrinter

def main(raw_argv):
    opts, argv = getopt(raw_argv)
    help = False
    version = False
    for o, v in opts:
        if o in ('-h', '--help'):
            help = True
        if o in ('-v', '--version'):
            version = True
    if help:
        show_version()
        show_help(argv)
        return 0
    if version:
        show_version()
        return 0
    if not argv:
        return console.main([])
    if argv[0] == 'console':
        return console.main(argv[1:])
    elif argv[0] == 'server':
        return web.main(argv[1:])
    elif argv[0] == 'profiler':
        return profiler.main(argv[1:])
    else:
        return console.main(argv)


def getopt(args):
    opts = []
    idx = 0
    for i, x in enumerate(args):
        if x in ('-h', '--help', '-v', '--version'):
            opts.append((x, None))
            idx = i
        else:
            break
    return opts, args[idx:]


def show_help(argv):
    op = OptPrinter()
    op.add(u'Usage: python stdcaty.py <commands> [opts]')
    op.add(u'\nコマンド一覧:')
    op.add(u'console', u'Catyコンソールを開く（コマンド省略時の動作）')
    op.add(u'server', u'Catyサーバを起動する')
    op.add(u'\nグローバルオプション:')
    op.add(u'-h, --help', u'このヘルプを表示する')
    op.add(u'-v, --version', u'バージョンを表示する')
    op.add(u'\n各コマンドのヘルプは python stdcaty.py command -h で表示される')
    op.show()


def show_version():
    print u'Caty', __version__


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
