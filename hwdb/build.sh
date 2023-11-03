#!/bin/bash

curdir=$(dirname $(realpath $0))

mkdir -p ${curdir}/platform/build

pushd ${curdir}/platform/build

cmake .. && make -j

popd
