# coding: utf-8
from topdown import *
from caty.util import merge_dict, try_parse

__all__ = ['to_decl_style']

def to_decl_style(s):
    return validator.run(s, auto_remove_ws=True)

@as_parser
def validator(seq):
    l = many(path)(seq)
    tree = reduce(lambda x, y:merge_dict(x, y, is_same_schema), l)
    return convert_schema(tree)

def path(seq):
    tokens = split([root, number, name, i_wild, o_wild, quoted_name], '.')(seq)
    _ = seq.parse(':')
    schema = seq.parse(name)
    _ = seq.parse(';')
    tree = reduce(lambda x, y: {y: x}, reversed(tokens + [schema]))
    return tree

def root(seq):
    return seq.parse('$')

def name(seq):
    return seq.parse(Regex(r'[^ "$#*:.;]+'))

def quoted_name(seq):
    _ = seq.parse('"')
    s = seq.parse(until('"'))
    _ = seq.parse('"')
    return '"%s"' % s

def number(seq):
    return seq.parse(Regex(r'[0-9]+'))

def o_wild(seq):
    return seq.parse('*')

def i_wild(seq):
    return seq.parse('#')

def is_same_schema(a, b):
    u"""パス式の推論上での衝突判定関数。
    次のようなパス式でスキーマを書いた場合、処理の都合上衝突が起こってしまう。

    $.foo: array
    $.foo.#: string

    この場合、 $.foo.#: string から $.foo が array[string*] だと導出され、
    array は array[string*] を包含するため、このスキーマは妥当なスキーマとなる。
    それに対して、次のケースではエラーとなる。

    $.bar: array[string*]
    $.bar.#: integer

    array[string*] と array[intger*] はまったく包含関係にないので、これはエラーである。
    ただし現在の実装では厳密な型検査は行っておらず、上記のケースでは array[intger*] に修正される。
    
    次のようなケースは常にエラーとなる。

    $.bar: string
    $.bar: string
    """
    if isinstance(a, dict):
        if b.strip().startswith('array') and is_array(a):
            return a
        if b.strip().startswith('object') and is_object(a):
            return a
        raise Exception()
    elif isinstance(b, dict):
        if a.strip().startswith('array') and is_array(b):
            return b
        if a.strip().startswith('object') and is_object(b):
            return b
        raise Exception()
    else:
        raise Exception()

def is_array(d):
    for k in d.keys():
        if k != '#' and try_parse(int, k) == None:
            return False
    return True

def is_object(d):
    return not is_array(d)

def convert_schema(tree, root=True):
    u"""パス式から変換された木（実際は辞書）を文字列形式に変換する。
    引数の tree は単一のスキーマの場合もある。
    """
    def _handle_array(dct):
        def _convert(v):
            if isinstance(v, dict):
                return 'object {%s}' % convert_schema(v, False)
            else:
                return v
        if '#' in dct and len(dct) == 1: # '#' だけが指定された場合
            v = dct['#']
            return ('array [%s*]' % _convert(v))
        else: # インデックスも指定されている場合
            keys = filter(lambda x: x, map(lambda x:try_parse(int, x), dct.keys()))
            keys.sort()
            l = []
            for k in map(str, keys):
                l.append(_convert(dct[k]))
            if '#' in dct: # '#' が指定された場合
                l.append(_convert(dct['#'])+'*')
            return 'array [%s]' % ', '.join(l)

    def _convert():
        if not isinstance(tree, dict):
            yield tree
        else:
            lval = ''
            for k, v in tree.iteritems():
                if k == '$':
                    lval = 'type $ = '
                else:
                    lval = '"%s" : ' % k
                if isinstance(v, basestring):
                    yield lval + v
                elif isinstance(v, dict):
                    if is_array(v):
                        yield lval + _handle_array(v)
                    else:
                        yield lval + ('object {%s}' % convert_schema(v, False))

    return ', '.join(list(_convert())) + (';' if root else '')

