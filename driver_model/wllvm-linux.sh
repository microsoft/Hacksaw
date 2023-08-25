#!/bin/bash
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

set -x

pushd linux-5.19.17

export LLVM_COMPILER=clang
cp ../wllvm.config .config
make CC=wllvm olddefconfig
make CC=wllvm -j$(nproc)

popd
