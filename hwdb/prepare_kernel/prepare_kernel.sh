#!/bin/bash

KERN_SRC="$1"

curdir=$(dirname $(realpath $0))

pushd ${KERN_SRC}

mkdir -p build_llvm
#make -j4 CC=clang allyesconfig O=./build_llvm
make -j$(nproc) CC=clang allmodconfig O=./build_llvm
make -j$(nproc) CC=clang O=./build_llvm
make -j$(nproc) CC=clang INSTALL_MOD_PATH=./mod_install modules_install O=./build_llvm

${curdir}/buildir.py $(realpath ./build_llvm)
${curdir}/linkir.py $(realpath ./build_llvm)

popd
