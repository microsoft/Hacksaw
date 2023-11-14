#!/bin/bash
#
if [ $# -eq 2 ]; then
  KERNEL_VER="$1"
  TARGET_CONFIG_FILE=$(realpath $2)
else
  echo "Usage: $0 <KERNEL_VER> <CONFIG_FILE>"
  exit 1
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
BUILDDIR="${ROOTDIR}/build/"
KERNEL_TARGET_BUILD_PATH="$BUILDDIR/linux-${KERNEL_VER}-target/"
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"
BCLIST="${OUTPUT_PATH}/target-allbc.list"

$ROOTDIR/kernel/build_target_kernel.sh $KERNEL_VER $TARGET_CONFIG_FILE

mkdir -p $OUTPUT_PATH

${ROOTDIR}/hwdb/build.sh
rm -f ${KERNEL_TARGET_BUILD_PATH}/vmlinux.o
find $KERNEL_TARGET_BUILD_PATH -name "*.bc" > $BCLIST
${BUILDDIR}/platform/callgraph -f $BCLIST

${ROOTDIR}/hwdb/prepare_database/gen_objdep.sh $KERNEL_TARGET_BUILD_PATH
