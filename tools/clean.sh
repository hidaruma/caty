#!/bin/sh

rm -f log.txt log.txt.* storage.db

find -name '*.log' -or -name '*.ctpl' -or -name '*.icaty' -or -name '*.pyc' | tee gomi.list | xargs rm
