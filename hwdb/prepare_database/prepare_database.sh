#!/bin/bash

KERN_SRC=$(realpath "$1")
curdir=$(dirname $(realpath $0))

find ${KERN_SRC}/build_llvm -name "*.bc" > ${curdir}/allbc.list
${curdir}/modinitcb.sh ${KERN_SRC}
${curdir}/modinitcb.py ${KERN_SRC}
