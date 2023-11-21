#!/bin/bash

CURDIR=$(dirname $(realpath $0))

usage() {
  echo "Usage: [docker stuff...] -- COMMAND" 1>&2
  echo ""
  echo "Commands:" 1>&2
  echo "  extract   Extract /boot and /lib/modules" 1>&2
  echo "  update    Update system image using patched kernel files" 1>&2
  exit 1
}

if [ $# -le 1 ]; then
  usage
fi

if [ "$2" = "extract" ]; then
  shift 2
  source $CURDIR/extract.sh 
elif [ "$2" = "update" ]; then
  shift 2
  source $CURDIR/update.sh 
else
  usage
fi
