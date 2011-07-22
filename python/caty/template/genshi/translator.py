# coding: utf-8
from HTMLParser import HTMLParser
from StringIO import StringIO
import re

def split_seq(f, seq):
    u"""リストを f でフィルターし、真のリストと偽のリストに分ける
    """
    tl = []
    fl = []
    for i in seq:
        if f(i):
            tl.append(i)
        else:
            fl.append(i)
    return tl, fl

def attr_sort(a, b):
    u"""Caty 名前空間の属性のソートを行う。
    switch > block > if > for という優先順位を付ける。
    こうする事でブロックとして扱うかどうかを決定しやすくする。
    """
    if a[0] == 'switch':
        return -1
    elif b[0] == 'switch':
        return 1
    else:
        if a[0] == 'block':
            return -1
        elif b[0] == 'block':
            return 1
        else:
            return cmp(a, b)

def take1st(seq):
    for fst, snd in seq:
        yield fst

ALLOWED_COMBINATION = (
    frozenset(['if', 'for', 'block']),
    frozenset(['if', 'for', ]),
    frozenset(['for', 'block']),
    frozenset(['if', 'block']),
    frozenset(['for',]),
    frozenset(['if',]),
    frozenset(['switch', 'case', 'block']),
    frozenset(['switch', 'case']),
    frozenset(['switch',]),
    frozenset(['case','block',]),
    frozenset(['case',]),
    frozenset(['block',]),
    frozenset(['include-href',]),
    frozenset(['replace',]),
    frozenset(['content',]),
)
def verify_attr(attrs, startend=False):
    u"""属性の組み合わせについて、明らかにおかしいものを検出する。
    空要素への c:content、c:content と c:replace の同時指定、
    c:if と c:case の同時指定など。
    許される組み合わせは以下の通りに限られるので、それを除く組み合わせはすべてエラーとする。
    if, for, block
    if, for
    if, block
    if,
    for,
    for, block
    switch, case, block
    switch, case
    case, block
    switch,
    case,
    block,
    include-href
    replace
    content
    """
    if startend and 'content' in attrs:
        return False
    return frozenset(attrs) in ALLOWED_COMBINATION

class GenshiTemplateError(Exception):
    pass

class GenshiTranslator(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._buffer = StringIO()
        self._prefix = 'c:'
        self._tag_depth = 0 # タグのネストの深さ
        self.caty_ns = 'http://chimaira.org/caty/template'
        self._last_block_queue = [] # この値が空値でなければブロックの終了要素（{/if}など）を追加する。
        self._block_end_queue = [] # フラグメントブロックに対応するためのフィールド。block=endが出現したら、 _last_block_queue に移す
        self._switch_queue = [] # 非ラッパー要素の switch 文
        self._wrapper_switch_queue = [] # ラッパー要素の switch 文
        self._switch_var_queue = []
        self._content = () # c:content に対応。タグ名と深さと content 属性の値を保持
        self._replace = () # c:replace に対応
        self._variable_pattern = re.compile(r'\$\{ *([a-zA-Z]+([a-zA-Z0-9]|\.)*(\|[a-zA-Z]+[a-zA-Z0-9]*(:".+?")*)*) *\}')

    def __str__(self):
        if self._tag_depth != 0:
            raise GenshiTemplateError('miss matched tag')
        self._buffer.seek(0)
        return self._buffer.read()

    buffer = property(lambda self: self._buffer)

    def set_prefix(self, p):
        self._prefix = p

    def handle_starttag(self, tag, attrs):
        self._tag_depth += 1
        tag, attr = self._handle_starttag(tag, attrs)
        # 要素置換があるなら即リターン
        if self._replace:
            return
        # 内容置換がある場合、内容置換の定義された要素のみ出力
        # <c:content...><elem>... の場合、 elem は出力されない
        if not self._content or self._content[0] == tag and self._content[1] == self._tag_depth:
            if attr:
                self._buffer.write('<%s %s>' % (tag, attr))
            else:
                self._buffer.write('<%s>' % (tag))

    def handle_startendtag(self, tag, attrs):
        self._tag_depth += 1
        tag, attr = self._handle_starttag(tag, attrs)
        if not self._replace:
            self._buffer.write('<%s %s/>' % (tag, attr))
        self._insert_end_block(tag, True)
        self._tag_depth -= 1

    def _handle_starttag(self, tag, attrs):
        if tag == 'html':
            for p, n in attrs:
                if n == self.caty_ns:
                    self.set_prefix(p.replace('xmlns:', '') + ':')
        catyattrs, htmlattrs = split_seq(lambda v: v[0].startswith(self._prefix), attrs)
        catyattrs = [(c[0].split(':', 1)[1], c[1]) for c in catyattrs]
        if self._switch_queue and 'case' not in take1st(catyattrs):
            if self._switch_queue[-1] == self._tag_depth and not (self._block_end_queue and self._block_end_queue[-1][1] == self._switch_queue[-1]):
                self._buffer.write('{/switch}')
        self._handle_caty_syntax(tag, catyattrs)
        attr = ' '.join(['%s="%s"' % (a[0], a[1]) for a in htmlattrs])
        return tag, attr
    
    def _handle_caty_syntax(self, tag, attrs):
        if not attrs:
            return
        attr_names = [n for n, v in attrs]
        if not verify_attr(attr_names):
            raise GenshiTemplateError('Not allowed combination of attribute in %s: %s' % (tag, ', '.join(attr_names)))
        attrs.sort(cmp=attr_sort)
        is_block = False # 複数の要素にまたがるフラグメントブロックか?
        for name, value in attrs:
            if name == 'if':
                self._buffer.write('{if $%s}' % value)
                if not is_block: # フラグメントブロックでないなら即座にブロックを閉じる
                    self._last_block_queue.append((tag, self._tag_depth, '{/if}'))
                else:
                    self._block_end_queue.append((tag, self._tag_depth, '{/if}'))
            elif name == 'for':
                item, seq = value.split(' in ')
                self._buffer.write('{foreach item=%s from=$%s}' % (item, seq))
                if not is_block: # フラグメントブロックでないなら即座にブロックを閉じる
                    self._last_block_queue.append((tag, self._tag_depth, '{/foreach}'))
                else:
                    self._block_end_queue.append((tag, self._tag_depth, '{/foreach}'))
            elif name == 'case':
                sw = self._switch_var_queue[-1]
                if sw[0]:
                    sw[0] = False
                    self._buffer.write('{if $%s|eq:"%s"}' % (sw[1], value))
                else:
                    self._buffer.write('{elif $%s|eq:"%s"}' % (sw[1], value))
                if not is_block: # フラグメントブロックかどうかは関係ないが、処理の都合上空文字を入れておく
                    self._last_block_queue.append((tag, self._tag_depth, ''))
                else:
                    self._block_end_queue.append((tag, self._tag_depth, ''))
            elif name == 'switch':
                self._switch_var_queue.append([True, value])
                if 'case' in attr_names: # 非ラッパー要素として働く場合
                    self._switch_queue.append(self._tag_depth)
                else: #ラッパー要素として働く場合
                    self._last_block_queue.append((tag, self._tag_depth, '{/switch}'))
            elif name == 'default':
                self._buffer.write('{else}')
                if not is_block: # フラグメントブロックかどうかは関係ないが、処理の都合上空文字を入れておく
                    self._last_block_queue.append((tag, self._tag_depth, ''))
                else:
                    self._block_end_queue.append((tag, self._tag_depth, ''))
            elif name == 'content':
                self._content = (tag, self._tag_depth, '{$%s}' % value)
            elif name == 'replace':
                self._replace = (tag, self._tag_depth, '{$%s}' % value)
            elif name == 'include-href':
                self._replace = (tag, self._tag_depth, '{include file="%s"}' % value)
            elif name == 'block':
                v = value.strip().lower()
                if v == 'start':
                    is_block = True
                elif v == 'end':
                    t, d, c = self._block_end_queue.pop(-1)
                    close_elem = (tag, d, c)
                    self._last_block_queue.append(close_elem)
            else:
                raise GenshiTemplateError('Unknown attribute: %s' % name)

    def _insert_end_block(self, tag, startend=False):
        if self._switch_queue and (self._switch_queue[-1] - 1 == self._tag_depth):
            self._buffer.write('{/if}')
            self._switch_var_queue.pop()
        if not self._replace:
            if self._content and self._content[0] == tag and self._content[1] == self._tag_depth:
                self._buffer.write(self._content[2])
                self._content = ()
            # switch は if や foreach と違い、ラッパー要素の中にないとダメ。
            # かなり汚いけど、 switch のみは終了タグの前に {/if} をバッファに書き出す
            if self._last_block_queue and self._last_block_queue[-1][1] == self._tag_depth and self._last_block_queue[-1][0] == tag:
                encloser = self._last_block_queue[-1][2]
                if encloser == '{/switch}':
                    self._buffer.write('{/if}')
            if not startend:
                self._buffer.write('</%s>' % tag)
            if self._last_block_queue and self._last_block_queue[-1][1] == self._tag_depth and self._last_block_queue[-1][0] == tag:
                encloser = self._last_block_queue.pop(-1)[2]
                if encloser == '{/switch}':
                    self._switch_var_queue.pop()
                    encloser = ''
                self._buffer.write(encloser)
        else:
            if self._replace[0] == tag and self._replace[1] == self._tag_depth:
                self._buffer.write(self._replace[2])
                self._replace = ()


    def handle_endtag(self, tag):
        self._insert_end_block(tag)
        self._tag_depth -= 1

    def _write_when_no_content_or_replace(f):
        def _(self, *args):
            if self._replace or self._content:
                return
            else:
                return f(self, *args)
        return _

    @_write_when_no_content_or_replace
    def handle_data(self, data):
        data = self._variable_pattern.sub('{$\\1}', data)
        self._buffer.write(data)

    @_write_when_no_content_or_replace
    def handle_charref(self, name):
        self._buffer.write('&%s;' % name)

    @_write_when_no_content_or_replace
    def handle_entityref(self, name):
        self._buffer.write('&%s;' % name)

    @_write_when_no_content_or_replace
    def handle_comment(self, data):
        self._buffer.write(data)

    def handle_pi(self, data):
        if data.endswith('?'):
            self._buffer.write('<?%s>' % data)
        else:
            self._buffer.write('<?%s?>' % data)

