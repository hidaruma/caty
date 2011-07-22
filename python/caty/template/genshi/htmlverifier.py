# coding: utf-8
from BeautifulSoup import BeautifulSoup, NavigableString

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding='utf-8'):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        if self.endswith('?'):
            return "<?%s>" % self.toEncoding(output, encoding)
        else:
            return "<?%s?>" % self.toEncoding(output, encoding)

class HTMLVerifier(BeautifulSoup):
    u"""閉じタグが省略された HTML 文書をタグを補完した状態に変換する。
    BeautifulSoup の機能で殆ど事足りるが、 PI の処理だけはオーバーライドする必要がある。
    BeautifulSoup は Python の SGML ライブラリに依存しており、
    SGML と XML では PI の書式に差異があり、 SGML ではデリミタが '>' なのに対して
    XML では '?>' がデリミタとなる。
    caty では XML スタイルの PI を用いるため、普通に BeautifulSoup を使うと
    出力結果の PI が <?pi data??> のように ? が重複する結果となる。
    """
    def handle_pi(self, data):
        self._toStringSubclass(data, ProcessingInstruction)

def convert(htmlstr):
    u"""閉じタグが省略された HTML 文書をタグを補完した状態に変換する。
    """
    return str(HTMLVerifier(htmlstr))

