#!/bin/sh

rm -f log.txt log.txt.* storage.db

find -name '*.ctpl' -or -name '*.icaty' -or -name '*.pyc' -print0 | xargs -0 rm
