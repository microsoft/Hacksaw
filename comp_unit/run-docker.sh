#!/bin/bash
set -e

if [ ! -f builtin-objs.db ]; then
  cat ../driver_model/out/builtin-objs.db | sed 's/^\/.*linux-[0-9]\+\.[0-9]\+\.[0-9]\+\///' > builtin-objs.db
fi

docker run -it --rm -v $PWD:/mnt -u $(id -u):$(id -g) hacksaw:0.1 sh -c "cd /mnt && ./test-comp-unit.sh"
