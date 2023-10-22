#!/bin/bash

kver=${KERNEL_VER:-none}
OUTPUT_PATH="/hacksaw/out/$kver/"

if [ "$kver" != "none" ]; then
  /hacksaw/kernel/prepare_kernel.sh $kver

  /hacksaw/hwdb/gendb.sh $kver &
  /hacksaw/comp_unit/do-comp-unit.sh $kver &
  /hacksaw/driver_model/do-driver-model.sh $kver &

  while true
  do
    if [ -f /tmp/hw.done ]; then
      if [ -f /tmp/drvmod.done ]; then
        if [ -f /tmp/compunit.done ]; then
          break
        fi
      fi
    fi
    sleep 5
  done
else
  sleep infinity
fi