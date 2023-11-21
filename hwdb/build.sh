#!/bin/bash

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
BUILDDIR="${ROOTDIR}/build/"
PLATFORM_SRC_PATH=$(realpath "${CURDIR}/platform")
PLATFORM_BUILD_PATH="$BUILDDIR/platform"

mkdir -p $PLATFORM_BUILD_PATH
pushd $PLATFORM_BUILD_PATH
cmake $PLATFORM_SRC_PATH && make -j$(nproc)
popd
