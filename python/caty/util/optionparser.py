#coding:utf-8
import optparse

class OptionParseFailed(Exception): pass
class HelpFound(Exception): pass
class OptionParser(optparse.OptionParser):
    u"""標準の OptionParser はヘルプの出力と引数の解析エラー時に強制終了（!）してしまう。
    このクラスでは代わりに例外を送出することとし、呼び出し元にその後の処理を任せる。
    """
    def _get_args(self, args):
        return args[:] if args != None else []

    def exit(self, status=0, msg=''):
        raise HelpFound(msg)

    def error(self, msg):
        raise OptionParseFailed(msg)
    
