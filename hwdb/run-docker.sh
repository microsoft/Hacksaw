#!/bin/bash
set -e

KERNEL_VER="5.19.17"

docker run -it --rm -v $PWD:/hacksaw -u $(id -u):$(id -g) hacksaw:0.1 /bin/bash -c "cd /hacksaw && ./hwdb/build.sh"
docker run -it --rm -v $PWD:/hacksaw -u $(id -u):$(id -g) hacksaw:0.1 /bin/bash -c "cd /hacksaw && ./hwdb/gendb.sh ./build/linux-${KERNEL_VER}"
