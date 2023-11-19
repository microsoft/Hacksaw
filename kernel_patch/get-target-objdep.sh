#!/bin/bash
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
KERNEL_NOINLINE_BUILD_PATH="$BUILDDIR/linux-${KERNEL_VER}-noinline/"
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"
TARGET_BCLIST="${OUTPUT_PATH}/target-allbc.list"
NOINLINE_BCLIST="${OUTPUT_PATH}/noinline-allbc.list"

$ROOTDIR/kernel/build_target_kernel.sh $KERNEL_VER $TARGET_CONFIG_FILE NOINLINE

mkdir -p $OUTPUT_PATH

${ROOTDIR}/hwdb/build.sh
rm -f ${KERNEL_TARGET_BUILD_PATH}/vmlinux.o
find $KERNEL_TARGET_BUILD_PATH -name "*.bc" > $TARGET_BCLIST
${BUILDDIR}/platform/callgraph -f $TARGET_BCLIST

if [ -d "$KERNEL_NOINLINE_BUILD_PATH" ]; then
  find $KERNEL_NOINLINE_BUILD_PATH -name "*.bc" > $NOINLINE_BCLIST
  ${BUILDDIR}/platform/callgraph -f $NOINLINE_BCLIST
  ${CURDIR}/copy_noinline_imptab.sh $KERNEL_NOINLINE_BUILD_PATH $KERNEL_TARGET_BUILD_PATH
fi

${CURDIR}/gen_objdep.sh $KERNEL_TARGET_BUILD_PATH
${CURDIR}/touch-nonbc-objs.sh $KERNEL_TARGET_BUILD_PATH
