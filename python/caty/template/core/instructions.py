# coding: utf-8
LOAD = 0 # LOAD <KEY>: コンテキストからデータを取得し、スタックに積む
PUSH = 1 # PUSH <DATA>: 無名のデータをスタックに積む。このデータは数値か文字列のリテラルとする
POP = 2 # POP: スタックから値を一つポップする（POP されたデータはインタープリタの callee に渡される）
LABEL = 3 # LABEL <NAME>: ラベルを定義する（JMP で使用する）
JMP = 4 # JMP <NAME>: NAME で指定されたラベルにジャンプする
JMPUNLESS = 5 # JMPUNLESS <NAME>: スタックから値をポップし、その値が偽であればラベルにジャンプする
NEWCTX = 6 # NEWCTX: コンテキストリストを伸長する
DELCTX = 7 # DELCTX: コンテキストリストの最初の要素を削除する（初期コンテキストを削除してはならない）
CPUSH = 8 # CPUSH <KEY>: スタックからポップした値をコンテキストに <NAME> というキーで追加（初期コンテキストには NG）
MACRO = 9 # MACRO <KEY>: <NAME> という名前のマクロ定義を開始（現状入れ子不可）
RETURN = 10 # RETURN: マクロの終了。スタックから戻り先アドレスをポップし、そこにジャンプする
EXPAND = 11 # EXPAND <NAME>: NAME で指定されたマクロを呼び出す
STRING = 12 # STR <LITERAL>: 文字列リテラルを callee に渡す
DEFINED = 13 # DEFINED <KEY>: コンテキストに KEY があれば True を、そうでなければ False をスタックに積む
CALL = 14 # CALL <NAME> <ARGC>: ARGC 個の引数で NAME 関数を呼び出し、戻り値をスタックに積む
INCLUDE = 15 # INCLUDE <NAME>: NAME で指定された別のテンプレートを呼び出す。事実上マクロと同じ
NOT = 16 # NOT: スタックトップの値を真偽反転する
ADD = 17 # ADD: スタックから値を二つ取り、それらを加算した値をスタックに積む
EQ = 18 # EQ: スタックから値を二つ取り、それらが等しいかどうかの結果をスタックに積む
LT = 19 # LT: EQ と同様に、最初にポップした要素の方が小さいかどうかをスタックに積む
LE = 20 # LE: LT と大体同じ
LEN = 21 # LEN: スタックトップから値を取り、その値の長さを返す
AT = 22 # AT: スタックから値を二つ取り、最初にポップしたデータを配列、二番目のものを添字として取得した値をスタックに積む
REFCONTEXT = 23 # REFCONTEXT: 現在のコンテキストをスタックに積む
ITEM = 24 # ITEM <KEY>: スタックから値をポップし、 <その値[KEY]> の値をスタックに積む 
ENUM = 25 # ENUM: スタックトップの値に enumerate を適用する
CDEL = 26 # CDEL <KEY>: コンテキストリストトップの値を削除する。主にループ処理で用いる
SUBCONTEXT = 27 # SUBCONTEXT <NAME>: サブテンプレートに渡すコンテキスト名。これが空のとき、親のコンテキストがすべて渡される
DISCARD = 28 # DISCARD: スタックトップの値を削除する
FUNCTION_DEF = 29 # FUNCTION_DEF <NAME>: <NAME>という名前の関数を定義
VALIDATE = 30 # VALIDATE <TYPE_NAME>: スタックトップの値を<TYPE_NAME>でバリデーションする
MASK_CONTEXT = 31 # CONTEXT_MASK: スタックトップの値をコンテキストとして扱い、実際のコンテキストを保護する
UNMASK_CONTEXT = 32 # CONTEXT_UNMASK: CONTEXT_MASKの動作を取り消す
CALL_TEMPLATE = 33 # CALL_TEMPLATE <NAME>: <NAME>テンプレートを呼び出す。テンプレートのコンテキストはスタックトップ
DISPATCH = 34 # FUNCTION_MATCH <TYPE>: コンテキストが<TYPE>に適合するかをスタックに詰む
GROUP_DEF = 35 # GROUP_DEF <NAME>: <GROUP>という名前の関数を定義
FUNCTION_MATCH = 36 # FUNCTION_MATCH <NAMESPACE>: <NAMESPACE>にパターンマッチを定義する
CALL_GROUP = 37 # CALL_GROUP <NAME>: <NAME>グループを呼び出す。テンプレートのコンテキストはスタックトップ
END_GROUP = 38 # END_GROUP: グループ定義の終わり

def get_name(code):
    d = {}
    for k, v in globals().items():
        if k[0].isupper() and k[-1].isupper():
            d[v] = k
    return d.get(code, 'UNKNOWN')

