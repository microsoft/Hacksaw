#!/bin/bash
set -e

BUILD_PATH="build/"
OUTPUT_PATH="out/"

KERNEL_VER="5.19.17"
KERNEL_PATH="$BUILD_PATH/linux-${KERNEL_VER}/"
KERNEL_CONF="dotconfig"
BUILTIN_OBJS="builtin-objs.db"
OBJ_KCONF_DB="${OUTPUT_PATH}/obj-kconf.db"
BUILD_DEP_OUT="${OUTPUT_PATH}/build-dep.raw"
BUILTIN_DEP="${OUTPUT_PATH}/builtin-objs.dep"

mkdir -p ${BUILD_PATH}
mkdir -p ${OUTPUT_PATH}

if [ ! -d "${KERNEL_PATH}" ]; then
  pushd $BUILD_PATH
  wget -c https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-${KERNEL_VER}.tar.xz -O - | tar -xJ
  popd
fi

if [ ! -f "${KERNEL_CONF}" ]
then
  pushd ${KERNEL_PATH}
  make allmodconfig
  popd
  cp ${KERNEL_PATH}/.config $KERNEL_CONF
fi

./get-obj-kconf-expr.py -k ${KERNEL_PATH} -o ${OUTPUT_PATH} -n $(nproc) > ${OBJ_KCONF_DB}
./get-build-deps.py -f ${OBJ_KCONF_DB} -c ${KERNEL_CONF} -b ${BUILTIN_OBJS} -n $(nproc) > ${BUILD_DEP_OUT}
cat ${BUILD_DEP_OUT} | ./gen-dep.py | sort | uniq > ${BUILTIN_DEP}
