# -*- coding: utf-8 -*-

# == 変数名
# pri_dir -- プロジェクトのディレクトリ
# app -- アプリケーション名
# app_dir -- アプリケーションのディレクトリ
# origin -- オリジン名
# origins -- オリジン名のリスト
# origin_dir -- オリジンのディレクトリ
# semver -- SemVer文字列 X.Y.Z 
# version -- バージョンのフル文字列
# prod -- プロダクト名
# prods_dir -- prods/ のディレクトリパス
# prod_dir -- プロダクトのディレクトリ
# install_target_short -- prj, glb, app のどれか



## プロジェクト内でアプリケーションを探す
# プロジェクトディレクトリを基点としたアプリケーションディレクトリパスを返す。
# アプリケーションが存在しないときは空文字列を返す。
#
function find_app { # (prj_dir, app) => *STDOUT*
  local prj_dir=$1
  local app=$2

  local app_dir=""
  for grp in main develop common extra examples; do
      if [ -d $prj_dir/$grp/$app ]; then
	  app_dir=$prj_dir/$grp/$app
	  echo $app_dir
	  return 0
      fi
  done
}

function get_semver { # (prod_dir) => *STDOUT*
    local prod_dir=$1

    if [ ! -f $prod_dir/SemVer.txt ]; then
	echo 0.0.0> $prod_dir/SemVer.txt
    fi
    local semver=$(cat $prod_dir/SemVer.txt)
    echo $semver
}

function confirm_version { # (prod_dir) => *STDOUT*
    local prod_dir=$1

    if [ ! -f $prod_dir/SemVer.txt ]; then
	echo 0.0.0> $prod_dir/SemVer.txt
    fi
    local semver=$(cat $prod_dir/SemVer.txt)

    if [ ! -f $prod_dir/Version.txt -o -n "$semver" ]; then
	echo "DEBUG:confirm_version: making Version.txt"
	make_version $semver > $prod_dir/Version.txt
    fi
    local version=$(cat $prod_dir/Version.txt)
    echo "DEBUG:confirm_version: version=$version"
    echo "$version"
}

function expand_template { # (prod_dir) => *STDOUT*
    local prod_dir=$1

#    if [ ! -f $prod_dir/Version.txt ]; then
#	make_version > $prod_dir/Version.txt
#    fi
    local version=$(cat $prod_dir/Version.txt)
    echo "DEBUG: version=$version"

    cat $prod_dir/package.template.json | sed -e 's/\$\$/\$/g' -e "s/\\\$version/$version/g" > $prod_dir/package.json
}

function make_version { # ($prod_dir) => *STDOUT*
    local semver=$(get_semver $prod_dir)

    local Suffix=r$(hg parent $File | grep ^changeset | cut -d: -f2,3 | sed -e 's/ //g' -e 's/:/./' ).$(date +%Y%m%d)
    
    echo $semver+$Suffix
}


function make_archive_name { # (prod_dir, install_target_suffix) => *STDOUT*
    local prod_dir=$1
    local install_target_suffix=$2

    if [ ! -f $prod_dir/SemVer.txt ]; then
	echo 0.0.0> $prod_dir/SemVer.txt
    fi
    local semver=$(cat $prod_dir/SemVer.txt)
#    echo "DEBUG:make_archive_name: semver=$semver"

    prod=$(echo $prod_dir | sed -e 's@/$@@' -e 's@^.*/@@')
#    echo "DEBUG:make_archive_name: prod_dir=$prod_dir"
#    echo "DEBUG:make_archive_name: prod=$prod"

    echo ${prod}_$semver.$install_target_suffix.zip
}


function list_origins { # (prj_dir) => *STDOUT*

  local prj_dir=$1

  if [ -d $prj_dir/prods ]; then
      echo project
  fi
  if [ -d $prj_dir/global/prods ]; then
      echo global
  fi

  for grp in main develop common extra examples; do
      if [ -d $prj_dir/$grp/ ]; then
	  local list=`/bin/ls -F $prj_dir/$grp/ | grep '/$' | sed -e 's@/@@'`
	  for app in $list; do
	      if [ -d $prj_dir/$grp/$app/prods ]; then
		  echo $app
	      fi
	  done
      fi
  done
}

function list_prods { # (prj_dir, origin) => *STDOUT*
  local prj_dir=$1
  local origin=$2
  local origin_dir

  case "$origin" in
      project)
	  origin_dir=$prj_dir
	  ;;
      global)
	  origin_dir=$prj_dir/global
	  ;;
      *)
	  origin_dir=$(find_app $prj_dir $origin)
	  ;;
  esac
#  echo "DEBUG: origin_dir=$origin_dir"

  local prods_dir=$origin_dir/prods
#  echo "DEBUG: prods_dir=$prods_dir"
  local list=$(/bin/ls -F $prods_dir 2>/dev/null | grep '^[^.]*/$' | sed -e 's@/@@')
#  echo "DEBUG: list=$list"
  for f in $list; do
      echo $f
  done
}

function list_all_prods {
  local prj_dir=$1

  local origins=$(list_origins $prj_dir)
#  echo "DEBUG: origins=$origins"
  local prods
  for ori in $origins; do
      prods=$(list_prods $prj_dir $ori)
#      echo "DEBUG: prods=$prods @ $ori"
      for prod in $prods; do
	  echo ::$ori:$prod
      done
  done
}

function list_all_prod_dirs {
  local prj_dir=$1

  local origins=$(list_origins $prj_dir)
#  echo "DEBUG: origins=$origins"
  local prods
  for ori in $origins; do
      prods=$(list_prods $prj_dir $ori)
#      echo "DEBUG: prods=$prods @ $ori"
      for prod in $prods; do
	  echo $prj_dir/$ori/prods/$prod
      done
  done
}

