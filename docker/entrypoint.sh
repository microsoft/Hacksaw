#!/bin/bash

kver=${KERNEL_VER:-none}

if [ "$kver" != "none" ]; then
  /hacksaw/kernel/prepare_kernel.sh $kver

  /hacksaw/hwdb/gendb.sh $kver
  /hacksaw/comp_unit/do-comp-unit.sh $kver
  /hacksaw/driver_model/do-driver-model.sh $kver
else
  sleep infinity
fi
