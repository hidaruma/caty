# -*- coding: utf-8 -*- 
# win32cls.py
#
# see http://d.hatena.ne.jp/m-hiyama/20091222/1261444695
#

from ctypes import windll, Structure, c_short, c_ushort, c_int, c_uint, byref

# Win32の型の定義: 
# SHORT, WORD, DWORD, 
# COORD, SMALL_RECT, CONSOLE_SCREEN_BUFFER_INFO

SHORT = c_short
WORD = c_ushort
DWORD = c_uint

class COORD(Structure):
  """struct in wincon.h."""
  _fields_ = [
    ("X", SHORT),
    ("Y", SHORT)]

class SMALL_RECT(Structure):
  """struct in wincon.h."""
  _fields_ = [
    ("Left", SHORT),
    ("Top", SHORT),
    ("Right", SHORT),
    ("Bottom", SHORT)]

class CONSOLE_SCREEN_BUFFER_INFO(Structure):
  """struct in wincon.h."""
  _fields_ = [
    ("dwSize", COORD),
    ("dwCursorPosition", COORD),
    ("wAttributes", WORD),
    ("srWindow", SMALL_RECT),
    ("dwMaximumWindowSize", COORD)]

# 定数の定義 winbase.h

STD_OUTPUT_HANDLE = -11

# Win32の変数と関数

stdout_handle = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
FillConsoleOutputCharacterA = windll.kernel32.FillConsoleOutputCharacterA
FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition

# pyreadline-1.7.1/pyreadline/console/cosole.py
#
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.
def fixcoord(x, y):
    u'''Return a long with x and y packed inside.'''
    
    # this is a hack! ctypes won't pass structures but COORD is 
    # just like a long, so this works.
    return c_int(y << 16 | x)

# 画面クリア

def clear_screen ():
  csbi = CONSOLE_SCREEN_BUFFER_INFO()
  coord = fixcoord(0, 0) # 初期値 coord.X = 0, coord.Y = 0
  dwDummy = DWORD()

  hConOut = stdout_handle
  if GetConsoleScreenBufferInfo (hConOut, byref(csbi)):
    FillConsoleOutputCharacterA (hConOut, 32, 
                                 csbi.dwSize.X * csbi.dwSize.Y, 
                                 coord, byref(dwDummy))
    FillConsoleOutputAttribute (hConOut, csbi.wAttributes, 
                                csbi.dwSize.X * csbi.dwSize.Y, 
                                coord, byref(dwDummy))
    SetConsoleCursorPosition (hConOut, coord)
