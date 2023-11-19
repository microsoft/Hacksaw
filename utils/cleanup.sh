#!/bin/bash
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <kernel version>"
	exit 1
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})

KERNEL_VER="$1"

rm -rf ${ROOTDIR}/build/linux-${KERNEL_VER} 2>/dev/null
rm -rf ${ROOTDIR}/build/linux-${KERNEL_VER}-noinline 2>/dev/null

find ${ROOTDIR}/build/linux-${KERNEL_VER}-target -type f \
	! \( -name '*.o.symtab' -o -name '*.o.imptab' -o -name '*.o.impnoin' -o -name '*.o.symlnk' -o -name '*.o.symcbs' -o -name '*.o.fptref' -o -name '*.o.nonbc' -o -name '*.mod' -o -name '*.ko' \) \
	-delete 2>/dev/null

find ${ROOTDIR}/build/linux-${KERNEL_VER}-target -type f \
	-name '.*' -o -name '*.mod.o' -o -name '*.mod.o.*' \
	-delete 2>/dev/null
