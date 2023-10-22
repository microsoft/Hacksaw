#!/bin/bash

if [ $# -ne 0 ]; then
  KERNEL_VER="$1"
else
  KERNEL_VER="5.19.17"
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
BUILDDIR="${ROOTDIR}/build/"
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"

KERNEL_SRC_PATH="$ROOTDIR/kernel/src/linux-$KERNEL_VER/"
KERNEL_BUILD_PATH="$BUILDDIR/linux-$KERNEL_VER/"

KMAX_BUILD_PATH="${BUILDDIR}/kmax-${KERNEL_VER}"
BUILTIN_OBJS="${OUTPUT_PATH}/builtin-objs.db"
OBJ_KCONF_DB="${OUTPUT_PATH}/obj-kconf.db"
BUILD_DEP_OUT="${OUTPUT_PATH}/build-dep.raw"
BUILTIN_DEP="${OUTPUT_PATH}/builtin-objs.dep"

if [ $# -eq 2 ]; then
  KERNEL_CONF="$2"
else
  KERNEL_CONF="$BUILDDIR/linux-$KERNEL_VER/.config"
fi

if [ ! -f "${KERNEL_CONF}" ]; then
  echo "$KERNEL_CONF does not exist."
  exit 1
fi

mkdir -p ${KMAX_BUILD_PATH}
mkdir -p ${OUTPUT_PATH}

if [ ! -d "$KERNEL_BUILD_PATH" ]; then
  echo "Linux kernel built is required. Run /kernel/prepare_kernel.sh $KERNEL_VER first"
  exit 1
fi

if [ ! -d "$KERNEL_SRC_PATH" ]; then
  wget -c https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VER:0:1}.x/linux-$KERNEL_VER.tar.xz -O - | tar -xJ -C $(dirname $KERNEL_SRC_PATH)
fi

${CURDIR}/get-builtin-objs.py -k $KERNEL_BUILD_PATH > $OUTPUT_PATH/builtin-objs.raw
cat $OUTPUT_PATH/builtin-objs.raw | sed "s/$LINUX_PREFIX//" | sort | uniq > $BUILTIN_OBJS

${CURDIR}/get-obj-kconf-expr.py -k ${KERNEL_SRC_PATH} -o ${KMAX_BUILD_PATH} -n $(nproc) > ${OBJ_KCONF_DB}
${CURDIR}/get-build-deps.py -f ${OBJ_KCONF_DB} -c ${KERNEL_CONF} -b ${BUILTIN_OBJS} -n $(nproc) > ${BUILD_DEP_OUT}
cat ${BUILD_DEP_OUT} | ${CURDIR}/gen-dep.py | sort | uniq > ${BUILTIN_DEP}
