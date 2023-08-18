#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

git clone --depth=1 -b release/15.x https://github.com/llvm/llvm-project.git ~/llvm-project

pushd gen_database
pushd platform
mkdir -p build
pushd build
cmake ..
make -j$(nproc)
popd

popd
