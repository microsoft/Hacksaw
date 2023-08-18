#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

pushd gen_database

pushd platform
git clone --depth=1 https://github.com/llvm/llvm-project.git -b release/15.x
mkdir -p build
pushd build
cmake ..
make -j$(nproc)
popd

popd
