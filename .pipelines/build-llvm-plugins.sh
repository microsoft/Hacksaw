#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

BUILD_PREFIX="${HOME}/hacksaw-build"
LLVM_SRC="${BUILD_PREFIX}/llvm-project-src"
LLVM_BUILD="${BUILD_PREFIX}/llvm-build"
LLVM_INSTALL="${BUILD_PREFIX}/llvm-install"
LLVM_VER="15.0.7"

if [ ! -d ${LLVM_INSTALL} ]
then
	mkdir -p ${LLVM_SRC}
	wget -c https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VER}/llvm-project-${LLVM_VER}.src.tar.xz -O - | tar -xJ --strip-components=1 -C ${LLVM_SRC}
	
	
	mkdir -p ${LLVM_BUILD}
	mkdir -p ${LLVM_INSTALL}
	
	cmake -G "Unix Makefiles" \
		-DCMAKE_BUILD_TYPE="Release" \
		-DLLVM_ENABLE_RTTI=On \
		-DBUILD_SHARED_LIBS=On \
		-DLLVM_ENABLE_DUMP=On \
		-DLLVM_TARGETS_TO_BUILD=X86 \
		-DLLVM_ENABLE_PROJECTS="clang" \
		-DCMAKE_INSTALL_PREFIX="${LLVM_INSTALL}" \
		-S ${LLVM_SRC}/llvm \
		-B ${LLVM_BUILD}
	
	pushd ${LLVM_BUILD}
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
fi

HWDB_BUILD="${BUILD_PREFIX}/hwdb"
mkdir -p ${HWDB_BUILD}
cmake -DLLVM_INCLUDE_PATH="${LLVM_INSTALL}/include" \
	-DLLVM_LIB_PATH="${LLVM_INSTALL}/lib" \
	-S hwdb/platform \
	-B ${HWDB_BUILD}

pushd ${HWDB_BUILD}
make -j$(nproc)
popd
