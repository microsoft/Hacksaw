#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

# git clone --depth=1 -b release/15.x https://github.com/llvm/llvm-project.git ~/llvm-project

pushd ~
https://github.com/llvm/llvm-project/releases/download/llvmorg-15.0.0/llvm-project-15.0.0.src.tar.xz
tar xf llvm-project-15.0.0.src.tar.xz 
popd

pushd gen_database
pushd platform
mkdir -p build
pushd build
cmake ..
make -j$(nproc)
popd

popd
