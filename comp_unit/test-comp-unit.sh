#!/bin/bash
set -e

KERNEL_PATH="linux-5.19.17/"
KERNEL_CONF="dotconfig"
OUTPUT_PATH="out/"
OBJ_KCONF_DB="${OUTPUT_PATH}/obj-kconf.db"
BUILD_DEP_DB="build-dep.db"

if [ ! -d "${KERNEL_PATH}" ]
then
	wget -c https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.19.17.tar.xz -O - | tar -xJ
fi

mkdir -p ${OUTPUT_PATH}

./get-obj-kconf-expr.py -k ${KERNEL_PATH} -o ${OUTPUT_PATH} -n $(nproc) > ${OBJ_KCONF_DB}
./get-build-deps.py -f ${OBJ_KCONF_DB} -c ${KERNEL_CONF} -n $(nproc) > ${BUILD_DEP_DB}
