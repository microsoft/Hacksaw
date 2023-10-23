#!/bin/bash

KERNEL_SRC_PATH="$1"
KERNEL_BUILD_PATH="$2"
OUTPUT_PATH="$3"
CURDIR=$(dirname $(realpath $0))

find $KERNEL_BUILD_PATH -name "*.bc" > ${OUTPUT_PATH}/allbc.log
${CURDIR}/modinitcb.sh ${KERNEL_SRC_PATH} ${OUTPUT_PATH}
${CURDIR}/modinitcb.py ${KERNEL_SRC_PATH} ${KERNEL_BUILD_PATH} ${OUTPUT_PATH}
${CURDIR}/gen_objdep.sh ${KERNEL_SRC_PATH} ${KERNEL_BUILD_PATH}
