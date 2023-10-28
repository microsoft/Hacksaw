#!/bin/bash

KERN_SRC="$1"

curdir=$(dirname $(realpath $0))

pushd ${KERN_SRC}

make mrproper
mkdir -p build_llvm
#make -j4 CC=clang allyesconfig O=./build_llvm
make -j$(nproc) CC=clang allmodconfig O=./build_llvm
sed -i "s/.*CONFIG_I2C_DESIGNWARE_PLATFORM.*/CONFIG_I2C_DESIGNWARE_PLATFORM=y/" build_llvm/.config
sed -i "s/^CONFIG_INTEL_SOC_PMIC_CHTWC.*//" build_llvm/.config
echo "CONFIG_INTEL_SOC_PMIC_CHTWC=y" >> build_llvm/.config
sed -i "s/^CONFIG_INTEL_SOC_PMIC_CHTDC_TI.*//" build_llvm/.config
echo "CONFIG_INTEL_SOC_PMIC_CHTDC_TI=m" >> build_llvm/.config
make -j$(nproc) CC=clang olddefconfig O=./build_llvm

make -j$(nproc) CC=clang O=./build_llvm
make -j$(nproc) CC=clang INSTALL_MOD_PATH=./mod_install modules_install O=./build_llvm

${curdir}/buildir.py $(realpath ./build_llvm)
${curdir}/linkir.py $(realpath ./build_llvm)

popd
