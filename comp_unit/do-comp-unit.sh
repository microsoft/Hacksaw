#!/bin/bash

if [ $# -eq 1 ]; then
  KERNEL_VER="$1"
else
  KERNEL_VER="5.19.17"
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
BUILD_PATH="${ROOTDIR}/build/"
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"

KERNEL_PATH="$BUILD_PATH/linux-${KERNEL_VER}/"
KERNEL_CONF="${OUTPUT_PATH}/dotconfig"
BUILTIN_OBJS="${OUTPUT_PATH}/builtin-objs.db"
OBJ_KCONF_DB="${OUTPUT_PATH}/obj-kconf.db"
BUILD_DEP_OUT="${OUTPUT_PATH}/build-dep.raw"
BUILTIN_DEP="${OUTPUT_PATH}/builtin-objs.dep"

mkdir -p ${BUILD_PATH}
mkdir -p ${OUTPUT_PATH}

if [ ! -d "${KERNEL_PATH}" ]; then
  pushd $BUILD_PATH
  wget -c https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VER:0:1}.x/linux-$KERNEL_VER.tar.xz -O - | tar -xJ
  popd
fi

if [ ! -f "${KERNEL_CONF}" ]
then
  pushd ${KERNEL_PATH}
  make allmodconfig
  popd
  cp ${KERNEL_PATH}/.config $KERNEL_CONF
fi

${CURDIR}/get-obj-kconf-expr.py -k ${KERNEL_PATH} -o ${OUTPUT_PATH} -n $(nproc) > ${OBJ_KCONF_DB}
${CURDIR}/get-build-deps.py -f ${OBJ_KCONF_DB} -c ${KERNEL_CONF} -b ${BUILTIN_OBJS} -n $(nproc) > ${BUILD_DEP_OUT}
cat ${BUILD_DEP_OUT} | ${CURDIR}/gen-dep.py | sort | uniq > ${BUILTIN_DEP}
