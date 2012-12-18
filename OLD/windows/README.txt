
The pyreadline package is a python implementation of GNU readline functionality
it is based on the ctypes based UNC readline package by Gary Bishop. 
It is not complete. It has been tested for use with windows 2000 and windows xp.

Features:
 *  NEW: keyboard text selection and copy/paste
 *  Shift-arrowkeys for text selection
 *  Control-c can be used for copy activate with allow_ctrl_c(True) is config file
 *  Double tapping ctrl-c will raise a KeyboardInterrupt, use ctrl_c_tap_time_interval(x)
    where x is your preferred tap time window, default 0.3 s.
 *  paste pastes first line of content on clipboard. 
 *  ipython_paste, pastes tab-separated data as list of lists or numpy array if all data is numeric
 *  paste_mulitline_code  pastes multi line code, removing any empty lines.
 *  Experimental support for ironpython. At this time Ironpython has to be patched for it to work.
 
 
 The latest development version is always available at the IPython subversion
 repository_.

.. _repository: http://ipython.scipy.org/svn/ipython/pyreadline/trunk#egg=pyreadline-dev
 

    Author: Jorgen Stenarson
    Author_email: jorgen.stenarson@bostream.nu
    Description: A python implmementation of GNU readline.
    Maintainer: Jorgen Stenarson
    Maintainer_email: jorgen.stenarson@bostream.nu
    Name: pyreadline
    Url: http://ipython.scipy.org/moin/PyReadline/Intro
    Version: 1.5
