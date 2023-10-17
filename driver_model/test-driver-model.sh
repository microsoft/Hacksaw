#!/bin/bash
set -x
set -e

KERNEL_VER="5.19.17"
KERNEL_PATH="linux-${KERNEL_VER}/"
KERNEL_CONF="wllvm.config"
OUTPUT_PATH="out/"

if [ ! -d "${KERNEL_PATH}" ]
then
  wget -c https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-${KERNEL_VER}.tar.xz -O - | tar -xJ
fi

cp $KERNEL_CONF ${KERNEL_PATH}/.config

pushd ${KERNEL_PATH}
export LLVM_COMPILER=clang
make CC=wllvm olddefconfig
make CC=wllvm -j$(nproc)
popd

mkdir -p ${OUTPUT_PATH}
