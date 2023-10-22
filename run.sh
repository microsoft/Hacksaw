#!/bin/bash

pushd docker
./build-docker.sh
popd

docker run -it --rm -v $PWD:/hacksaw -u $(id -u):$(id -g) -e KERNEL_VER="$KERNEL_VER" --name hacksaw hacksaw-rtti:0.1
