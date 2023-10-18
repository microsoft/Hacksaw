#!/bin/bash
set -e

DRVMOD_BUILTIN="../driver_model/out/builtin-objs.db"
COMPUN_BUILTIN="builtin-objs.db"

if [ ! -f $COMPUN_BUILTIN ]; then
  if [ -f $DRVMOD_BUILTIN ]; then
    cp $DRVMOD_BUILTIN $COMPUN_BUILTIN
  else
    echo "$COMPUN_BUILTIN does not exist."
  fi
fi

docker run -it --rm -v $PWD:/mnt -u $(id -u):$(id -g) hacksaw:0.1 sh -c "cd /mnt && ./test-comp-unit.sh"
