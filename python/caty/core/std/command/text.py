#coding: utf-8
from caty.core.command import Builtin
from caty.util.cx import creole2html

name = 'text'
schema = u"""
type RegexpMatch = {
    "src": string,
    "group": string,
    "groups": [string*],
};
"""

class Chop(Builtin):
    command_decl = u"""
        /**
         * 入力値の先頭と末尾から空白と改行を除去して返す。
         */
        command chop :: string -> string
            refers python:caty.command.text.Chop;
    """
    def execute(self, input):
        return input.strip()

class Trim(Builtin):
    command_decl = u"""
        /**
         * 入力値の先頭と末尾から引数の文字を除去して返す。
         */
        command trim [string] :: string -> string
            refers python:caty.command.text.Trim;
    """
    def setup(self, text):
        self.text= text

    def execute(self, input):
        while input.startswith(self.text):
            input = input[len(self.text):]
        while input.endswith(self.text):
            input = input[:-len(self.text)]
        return input

class Creole(Builtin):
    command_decl = u"""
        /**
         * 入力値を creole 記法の Wiki テキストだとみなし、 HTML に変換して返す。
         * このコマンドは後方互換性及び簡易的なアプリケーションのためにのみ存在する。
         * 応用的な理容には creole モジュールと xjx モジュールを使用すること。
         */
        command creole :: string -> string
            refers python:caty.command.text.Creole;
    """
    def execute(self, input):
        return creole2html(input)

class Join(Builtin):
    command_decl = u"""
        /**
         * 引数を区切り文字として入力値を連結して返す。
         */
        command join [string]:: [string*] -> string
            refers python:caty.command.text.Join;
    """
    def setup(self, sep):
        self.sep = sep

    def execute(self, input):
        return self.sep.join(input)

class Concat(Builtin):
    command_decl = u"""
        /**
         * 入力値を連結して返す。
         */
        command concat :: [string*] -> string
            refers python:caty.command.text.Concat;
    """

    def execute(self, input):
        return ''.join(input)

class ToUpper(Builtin):
    command_decl = u"""
        /**
         * 入力値を大文字にして返す。
         */
        command toupper :: string -> string
            refers python:caty.command.text.ToUpper;
    """
    def execute(self, input):
        return input.upper()

class ToLower(Builtin):
    command_decl = u"""
        /**
         * 入力値を小文字にして返す。
         */
        command tolower :: string -> string
            refers python:caty.command.text.ToLower;
    """
    def execute(self, input):
        return input.lower()

class Split(Builtin):
    command_decl = u"""
        /**
         * 入力値を引数の文字列で分割して返す。
         * 第二引数が与えられた場合、それ+1が分割数の最大値となる。
         */
        command split {} [string] :: string -> [string*]
                      {} [string, integer] :: string -> [string*]
            refers python:caty.command.text.Split;
    """
    def setup(self, sep, num=0):
        self.num = num
        self.sep = sep

    def execute(self, input):
        if self.num:
            return input.split(self.sep, self.num)
        else:
            return input.split(self.sep)

class RSplit(Builtin):
    command_decl = u"""
        /**
         * 入力値を引数の文字列で分割して返す。
         * 第二引数が与えられた場合、それ+1が分割数の最大値となる。
         * text:split との差異は、こちらは文字列を末尾から分割していく事である。
         */
        command rsplit {} [string] :: string -> [string*]
                       {} [string, integer] :: string -> [string*]
            refers python:caty.command.text.RSplit;
    """
    def setup(self, sep, num=0):
        self.num = num
        self.sep = sep

    def execute(self, input):
        if self.num:
            return input.rsplit(self.sep, self.num)
        else:
            return input.rsplit(self.sep)

from caty.template.genshi.htmlverifier import convert
from caty.util import get_charset
class CorrectHTML(Builtin):
    command_decl = u"""
    /**
     * 入力値の HTML を整形式の XHTML に修正する。
     *
     */
    command correct-html :: string | {*:any} -> string | {*:any}
        reads env
        refers python:caty.command.text.CorrectHTML;
    """
    def execute(self, input):
        if isinstance(input, unicode):
            return unicode(convert(input), self.env.get('APP_ENCODING'))
        else:
            cs = get_charset(input)
            input['body'] = unicode(convert(input['body']), cs or self.env.get('APP_ENCODING'))
            if 'content-length' in input['header']:
                input['header']['content-length'] = len(input['body'].encode(cs) if cs else input['body'])
            return input

from caty.jsontools import tagged
class RegMatch(Builtin):
    command_decl = u"""
    /**
     * 入力文字列が引数の正規表現パターンに合致するかどうかを返す。
     * 合致していれば @matched タグの付いたオブジェクトが返り、
     * 合致していなければ @fail タグの付いた入力文字列が返る。
     */
    command regmatch [string] :: string -> @match RegexpMatch | @fail string
        refers python:caty.command.text.RegMatch;
    """
    def setup(self, pattern):
        import re
        self.regexp = re.compile(pattern)

    def execute(self, input):
        m = self.regexp.search(input)
        if not m:
            return tagged(u'fail', input)
        else:
            return tagged(u'match', 
                {
                    'src': input,
                    'group': m.group(),
                    'groups': list(m.groups()),
                }
            )

