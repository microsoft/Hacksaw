#!/bin/bash

if [ $# -eq 1 ]; then
  KERNEL_VER="$1"
else
  KERNEL_VER="5.19.17"
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
SRCDIR="${ROOTDIR}/kernel/src/"
BUILDDIR="${ROOTDIR}/build/"
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"

KERNEL_SRC_PATH="$SRCDIR/linux-$KERNEL_VER/"
KERNEL_BUILD_PATH="$BUILDDIR/linux-$KERNEL_VER/"
KERNELRELEASE=$(cat ${KERNEL_BUILD_PATH}/include/config/kernel.release 2> /dev/null)

mkdir -p $OUTPUT_PATH

${CURDIR}/prepare_database/prepare_database.sh ${KERNEL_SRC_PATH} ${KERNEL_BUILD_PATH} ${OUTPUT_PATH}

${CURDIR}/build.sh

${BUILDDIR}/platform/platformdb \
    -i ${OUTPUT_PATH}/modinit.db \
    -a ${KERNEL_BUILD_PATH}/mod_install/lib/modules/${KERNELRELEASE}/modules.alias \
    -l ${OUTPUT_PATH}/allbc.list \
    -o ${OUTPUT_PATH}/hw.db

touch /tmp/hw.done
