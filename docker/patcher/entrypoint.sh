#!/bin/bash

kver=${KERNEL_VER:-none}

if [ "$kver" != "none" ]; then
  echo 'run patch scripts'
else
  echo 'hacksaw-patcher container is ready.'
  sleep infinity
fi
