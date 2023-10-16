#!/bin/bash

KERN_SRC=$(realpath "$1")
curdir=$(dirname $(realpath $0))
KERNELRELEASE=$(cat ${KERN_SRC}/build_llvm/include/config/kernel.release 2> /dev/null)

${curdir}/prepare_kernel/prepare_kernel.sh ${KERN_SRC}
${curdir}/prepare_database/prepare_database.sh ${KERN_SRC}

${curdir}/platform/build/callgraph -f ${curdir}/prepare_database/allbc.list
${curdir}/platform/build/platformdb \
    -i ${curdir}/prepare_database/modinit.db \
    -a ${KERN_SRC}/mod_install/lib/modules/${KERNELRELEASE}/modules.alias \
    -l ${curdir}/prepare_database/allbc.list \
    -o ${curdir}/hw.db
