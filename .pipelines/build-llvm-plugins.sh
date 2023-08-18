#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

pushd $HOME
wget -c https://github.com/llvm/llvm-project/releases/download/llvmorg-15.0.0/llvm-project-15.0.0.src.tar.xz -O - | tar -xz

mkdir -p llvm-project

pushd llvm-project
cmake -G "Unix Makefiles" \
	-DCMAKE_BUILD_TYPE="Release" \
	-DLLVM_ENABLE_RTTI=On \
	-DBUILD_SHARED_LIBS=On \
	-DLLVM_ENABLE_DUMP=On \
	-DLLVM_TARGETS_TO_BUILD=X86 \
	-DLLVM_ENABLE_PROJECTS="clang" \
	-S ../llvm-project-15.0.0.src/llvm \
	-B .

make -j$(nproc) LLVMCore LLVMSupport LLVMIRReader

popd # llvm-project
popd # $HOME

pushd gen_database
pushd platform
mkdir -p build
pushd build
cmake ..
make -j$(nproc)
popd
popd
