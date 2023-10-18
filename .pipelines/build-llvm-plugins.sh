#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

BUILD_PREFIX="${HOME}/hacksaw-build"
LLVM_INSTALL="${BUILD_PREFIX}/llvm-install"

HWDB_BUILD="${BUILD_PREFIX}/hwdb"
mkdir -p ${HWDB_BUILD}
cmake -DLLVM_INCLUDE_DIRS="${LLVM_INSTALL}/include" \
	-DLLVM_LIB_DIRS="${LLVM_INSTALL}/lib" \
	-S hwdb/platform \
	-B ${HWDB_BUILD}

pushd ${HWDB_BUILD}
make -j$(nproc)
popd

BUSCLASS_BUILD="${BUILD_PREFIX}/busclass"
mkdir -p ${BUSCLASS_BUILD}
cmake -S driver_model/llvm-pass-busclass \
	-B ${BUSCLASS_BUILD}

pushd ${BUSCLASS_BUILD}
make -j$(nproc)
popd

DRVDEV_BUILD="${BUILD_PREFIX}/drvdevreg"
mkdir -p ${DRVDEV_BUILD}
cmake -S driver_model/llvm-pass-drvdevreg \
	-B ${DRVDEV_BUILD}

pushd ${DRVDEV_BUILD}
make -j$(nproc)
popd
