#!/bin/bash
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <kernel version>"
	exit 1
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
BUILDDIR="${ROOTDIR}/build"

KERNEL_VER="$1"

KERNEL_BUILD_PATH="${BUILDDIR}/linux-${KERNEL_VER}"
KERNEL_NOINLINE_BUILD_PATH="${BUILDDIR}/linux-${KERNEL_VER}-noinline"
KERNEL_TARGET_BUILD_PATH="${BUILDDIR}/linux-${KERNEL_VER}-target"

rm -rf $KERNEL_NOINLINE_BUILD_PATH 2>/dev/null

if [ ! -L $KERNEL_TARGET_BUILD_PATH ]; then
	rm -rf $KERNEL_BUILD_PATH 2>/dev/null
fi

find $KERNEL_TARGET_BUILD_PATH -type f \
	! \( -name '*.o.symtab' -o -name '*.o.imptab' -o -name '*.o.impnoin' -o -name '*.o.symlnk' -o -name '*.o.symcbs' -o -name '*.o.fptref' -o -name '*.o.nonbc' -o -name '*.mod' \) \
	-delete 2>/dev/null

find $KERNEL_TARGET_BUILD_PATH -type f \
	-name '.*' -o -name '*.mod.o' -o -name '*.mod.o.*' \
	-delete 2>/dev/null
