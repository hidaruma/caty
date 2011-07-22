#!/bin/sh

files="RELEASE.txt CONTRIBUTORS.txt EXCUSE.txt INSTALL.txt LICENSE.ja-utf8.txt LICENSE.txt README.txt HISTORY.txt"

if [ "$1" == "-q" ]; then
    vopt=""
else
    vopt="--verbose"
fi
cp $vopt --update $files examples/readme/pub/

