-*- coding: utf-8 -*-

pyreadline-1.5-win32-setup.exe によりインストールされる pyreadline では、
CTRL-H の挙動に関してバグがあるようです。このバグに対して、清水川氏が次
のURLにてパッチを公開なさっています。

 - http://www.freia.jp/taka 清水川Web
 - http://www.freia.jp/taka/blog/690

さらに清水川氏はメールにより、次のパッチをご提供してくださいました。

--- keysyms.py.orig	2007-04-05 00:54:20 +0900
+++ keysyms.py	2010-01-08 18:17:05 +0900
@@ -119,6 +119,9 @@
        char = chr(VkKeyScan(ord(char)) & 0xff)
     elif control:
         char=chr(keycode)
+    if control and (ord(char),keycode) in ((8,72),(13,77)):
+      keycode=ord(char)
+      control=False
     try:
         keyname=code2sym_map[keycode]
     except KeyError:

このパッチ（ファイル keysyms.py.20100108.diff）を適用した keysyms.py が、
このREADME.Patch.txtと同一のディレクトリに置いてあります。パッチ適用済
み keysyms.py を、
PYTHON/Lib/site-packages/pyreadline/keysyms/keysyms.py と置き換えて（上
書きコピーして）ください。ここで、PYTHON は、Pythonがインストールされた
ディレクトリを表します。
