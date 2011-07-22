# coding: utf-8

def path_checker_combinator(path_checker, root_dir, function):
    u"""パス名のチェック関数と権限チェック関数と mafs ルートディレクトリと mafs 関数を受け取り、
    パス名のチェックとルートディレクトリの変更を行った上で mafs 関数を実行する関数を返す。
    """
    def wrapper(path, *args, **kwds):
        path_checker(path)
        return chroot(root_dir, function)(path, *args, **kwds)
    return wrapper

def default_path_checker(path):
    u"""パスが常に / から始まっており、また ./ ../ を含まないことをチェックする。
    チェックに引っかかった場合は例外が送出される。
    """
    if not path.startswith('/'): raise Exception('path must starts with "/"')
    if '/../' in path: raise Exception('Reference to parent directory is not allowed')
    if '/./' in path: raise Exception('Reference to current is not allowed')
    return path

def chroot(root, function):
    u"""root で指定されたディレクトリをルートディレクトリとして mafs 関数を動作させる。
    この関数は default_path_checker など .. を抑制する関数と組み合わせることを想定しており、
    そうでない場合はセキュリティ上の問題が発生しうる。
    """
    root = root.strip()
    if root.endswith('/'):
        root = root.rstrip('/')
    def wrapper(path, *args, **kwds):
        if not root.endswith('/') and not path.startswith(root):
            path = root + path
        return function(path, *args, **kwds)
    return wrapper

def trimroot(root, function):
    u"""chroot された mafs 関数から chroot された mafs 関数を呼ぶと、
    二重にディレクトリが移動されてしまう。
    それを防ぐため、一旦元のディレクトリに戻してから改めてパスを渡すこととする。
    """
    def wrapper(path, *args, **kwds):
        return function(path.replace(root, ''), *args, **kwds)
    return wrapper
