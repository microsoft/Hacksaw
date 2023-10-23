#!/bin/bash

pushd docker
./build-docker.sh
popd

docker run -it --rm -v $PWD:/hacksaw -u $(id -u):$(id -g) -e KERNEL_VER="$KERNEL_VER" \
  --name hacksaw-builder hacksaw-builder:0.1

docker run -it --rm -v $PWD:/hacksaw -u $(id -u):$(id -g) -e KERNEL_VER="$KERNEL_VER" \
  --cap-add SYS_ADMIN --device /dev/fuse --security-opt apparmor:unconfined \
  --name hacksaw-patcher hacksaw-patcher:0.1
