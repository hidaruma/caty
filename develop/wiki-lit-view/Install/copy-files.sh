#!/bin/sh

if [ "$1" = "" ]; then
    echo "Need one argument as target dir"
    exit 1
fi
THIS_NAME=`pwd | sed 's@.*/@@'`
TARGET=$1

echo "To $TARGET"
if [ $TARGET = $THIS_NAME ]; then
    echo "Same directory"; exit 1
elif [ ! -d $TARGET ]; then
    echo "Directory not exist"; exit 1
elif [ ! -f ./Install/files.list ]; then
    echo "Need ./Install/files.list"; exit 1
elif [ ! -f ./Install/exclude.list ]; then
    echo "Need ./Install/exclude.list"; exit 1
else
    tar cO --files-from ./Install/files.list --exclude-from ./Install/exclude.list \
	| tar xvf - -C $TARGET
fi
