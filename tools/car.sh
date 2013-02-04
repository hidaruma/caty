#!/bin/sh
# -*- coding: utf-8 -*-
# car -- Caty Archiver

DEFAULT_CATY_HOME=../caty
function find_caty_home { # () => $caty_home
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

# You can use the functions in $caty_home/tools/functions.sh

# ==== script body ====


function usage {
    echo "** Usage: $0 [option ...] origin prod"
    echo "** option:"
    echo "--project PROJECT_DIR"
    echo "--semver SEMANTIC_VERSION x.y.z"
}

prj_dir=.
semver=

while [ -n "$1" ]; do
    case "$1" in
	--project)
	    if [ -z "$2" ]; then
		echo "need option value for $1"; exit 1
	    else
		prj_dir=$2
		shift
	    fi
	    shift;;
	--semver)
	    if [ -z "$2" ]; then
		echo "need option value for $1"; exit 1
	    else
		semver=$2
		shift
	    fi
	    shift;;
	-*) echo "iilegal option $1"; exit 1;;
	*)  break;; # while ループを抜ける
    esac
done

debug "prj_dir=$prj_dir"
debug "semver=$semver"

if [ -z "$1" ]; then
    usage
    echo "** origin:"
    list_origins $prj_dir
    
    exit 1
fi
origin=$1

if [ -z "$2" ]; then
    usage
    echo "** product:"
    list_prods $prj_dir $origin

    exit 1
fi
prod=$2

debug "origin=$origin"
debug "prod=$prod"

case $origin in
    project)
	SUBEXT=caty-prj
	prod_dir=$prj_dir/products/$prod ;;
    global)
	SUBEXT=caty-glb
	prod_dir=$prj_dir/global/products/$prod ;;
    *)
	SUBEXT=caty-app
	app_dir=$(find_app $prj_dir $origin)
	prod_dir=$app_dir/products/$prod ;;
esac

debug "prod_dir=$prod_dir"

if [ ! -d $prod_dir ]; then
    echo "$prod_dir does not exist"; exit 1
fi

if [ ! -f $caty_home/tools/caty-archiver.py ]; then
    echo "cannot find archiver"
    exit 1
fi


fset=$prod_dir/files.fset

if [ ! -f "$fset" ]; then
    echo "Cannot find fset file: $fset"
    exit 1
fi

confirm_version $prod_dir $semver
expand_template $prod_dir


package_json=$prod_dir/package.json
debug "package_json=$package_json"

if [ ! -f "$package_json" ]; then
    echo "Cannot find package.json file: $package_json"
    exit 1
fi

archive_name=$(make_archive_name $prod_dir $SUBEXT)

debug "archive_name=$archive_name"

debug_exit

python $caty_home/tools/caty-archiver.py \
 --project=$prj_dir \
 --origin=$origin \
 --fset=$fset \
 --package-json=$prod_dir/package.json \
 $caty_home/dists/$archive_name

