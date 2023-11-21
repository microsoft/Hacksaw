#!/bin/bash

CURDIR=$(dirname $(realpath $0))

usage() {
  echo "Usage: [docker stuff...] -- COMMAND" 1>&2
  echo ""
  echo "Commands:" 1>&2
  echo "  prepare   Prepare hardware/kernel database" 1>&2
  echo "  analyze   Analyze dependencies of target kernel with its build configuration" 1>&2
  echo "  patch     Patch target system image" 1>&2
  exit 1
}

if [ $# -le 1 ]; then
  usage
fi

if [ "$2" = "prepare" ]; then
  shift 2
  source $CURDIR/prepare.sh 
elif [ "$2" = "analyze" ]; then
  shift 2
  source $CURDIR/analyze.sh 
elif [ "$2" = "patch" ]; then
  shift 2
  source $CURDIR/patch.sh 
else
  usage
fi
