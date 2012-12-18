#!/bin/sh
# -*- coding: utf-8 -*-

DEFAULT_CATY_HOME=../caty
function find_caty_home { # () => caty_home
    if [ -n "$CATY_HOME" ]; then
	caty_home=$CATY_HOME
    elif [ -d $DEFAULT_CATY_HOME ]; then
	caty_home=$DEFAULT_CATY_HOME
    else
	caty_home=.
    fi
}
find_caty_home
source $caty_home/tools/functions.sh

# You can use functions in $caty_home/tools/functions.sh

# ==== main ====


