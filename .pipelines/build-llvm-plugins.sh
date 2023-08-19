#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

pushd $HOME
wget -c https://github.com/llvm/llvm-project/releases/download/llvmorg-15.0.0/llvm-project-15.0.0.src.tar.xz -O - | tar -xJ
popd

mkdir -p $HOME/llvm-build
cmake -G "Unix Makefiles" \
	-DCMAKE_BUILD_TYPE="Release" \
	-DLLVM_ENABLE_RTTI=On \
	-DBUILD_SHARED_LIBS=On \
	-DLLVM_ENABLE_DUMP=On \
	-DLLVM_TARGETS_TO_BUILD=X86 \
	-DLLVM_ENABLE_PROJECTS="clang" \
	-DCMAKE_INSTALL_PREFIX="$HOME/llvm-install" \
	-S $HOME/llvm-project-15.0.0.src/llvm \
	-B $HOME/llvm-build

pushd $HOME/llvm-build
make -j$(nproc) LLVMCore LLVMSupport LLVMIRReader
make install-LLVMCore
make install-LLVMSupport
make install-LLVMIRReader

make install-LLVMAsmParser
make install-LLVMBinaryFormat
make install-LLVMBitReader
make install-LLVMBitstreamReader
make install-LLVMDemangle
make install-LLVMRemarks
make install-llvm-headers
popd

pushd gen_database
pushd platform
mkdir -p build
pushd build
cmake ..
make -j$(nproc)
popd
popd
