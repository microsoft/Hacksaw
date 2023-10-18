#!/bin/bash
set -x
set -e

KERNEL_VER="5.19.17"
KERNEL_PATH="linux-${KERNEL_VER}/"
KERNEL_CONF="dotconfig"
OUTPUT_PATH="out/"
OBJ_KCONF_DB="${OUTPUT_PATH}/obj-kconf.db"
BUILD_DEP_OUT="${OUTPUT_PATH}/build-dep.out"
OBJ_DEP="${OUTPUT_PATH}/objects.dep"

if [ ! -d "${KERNEL_PATH}" ]
then
  wget -c https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-${KERNEL_VER}.tar.xz -O - | tar -xJ
fi

if [ ! -f "${KERNEL_CONF}" ]
then
  pushd ${KERNEL_PATH}
  make allmodconfig
  popd
  cp ${KERNEL_PATH}/.config $KERNEL_CONF
fi

mkdir -p ${OUTPUT_PATH}

./get-obj-kconf-expr.py -k ${KERNEL_PATH} -o ${OUTPUT_PATH} -n $(nproc) > ${OBJ_KCONF_DB}
./get-build-deps.py -f ${OBJ_KCONF_DB} -c ${KERNEL_CONF} -n $(nproc) > ${BUILD_DEP_OUT}
cat ${BUILD_DEP_OUT} | ./gen-dep.py | sort > ${OBJ_DEP}
