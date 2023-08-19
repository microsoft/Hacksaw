#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

LLVMVER="15.0.7"
LLVMSRC="llvm-project-$LLVMVER.src"

pushd $HOME
wget -c https://github.com/llvm/llvm-project/releases/download/llvmorg-$LLVMVER/$LLVMSRC.tar.xz -O - | tar -xJ
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
	-S $HOME/$LLVMSRC/llvm \
	-B $HOME/llvm-build

pushd $HOME/llvm-build
make -j$(nproc) LLVMCore LLVMSupport LLVMIRReader

make install-LLVMAsmParser
make install-LLVMBinaryFormat
make install-LLVMBitReader
make install-LLVMBitstreamReader
make install-LLVMCore
make install-LLVMDemangle
make install-LLVMIRReader
make install-LLVMRemarks
make install-LLVMSupport
make install-LLVMTableGen
make install-LLVMTableGenGlobalISel
make install-llvm-headers
popd

pushd hwdb
pushd platform
mkdir -p build
pushd build
cmake ..
make -j$(nproc)
popd
popd
