#!/bin/bash

if [ $# -eq 1 ]; then
  KERNEL_VER="$1"
else
  KERNEL_VER="5.19.17"
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"
BUILD_PATH="${ROOTDIR}/build/"

KERNEL_PATH="$BUILD_PATH/linux-$KERNEL_VER/"
KERNEL_CONF="${OUTPUT_PATH}/dotconfig"
KERNEL_CONF_FRAGMENT="${CURDIR}/wllvm.kconfig.fragment"

BUSCLASS="busclass"
DRVDEV="drvdevreg"
DRVMOD_SRC=$(realpath "${CURDIR}/llvm-pass")
DRVMOD_PATH="$BUILD_PATH/drvmod"

mkdir -p $OUTPUT_PATH
mkdir -p $BUILD_PATH

if [ ! -d "$KERNEL_PATH" ]; then
  pushd $BUILD_PATH
  wget -c https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VER:0:1}.x/linux-$KERNEL_VER.tar.xz -O - | tar -xJ
  popd
fi
 
pushd $KERNEL_PATH
export LLVM_COMPILER=clang
make CC=wllvm mrproper 
make CC=wllvm allmodconfig
./scripts/kconfig/merge_config.sh .config $KERNEL_CONF_FRAGMENT
make CC=wllvm olddefconfig
make CC=wllvm -j$(nproc)
popd

cp ${KERNEL_PATH}/.config $KERNEL_CONF

mkdir -p $DRVMOD_PATH
pushd $DRVMOD_PATH
cmake $DRVMOD_SRC
make -j$(nproc)
popd

${CURDIR}/get-builtin-objs.py -k $KERNEL_PATH > $OUTPUT_PATH/builtin-objs.raw
${CURDIR}/extract-kernel-bc.py -k $KERNEL_PATH -b $OUTPUT_PATH/builtin-objs.raw -n $(nproc)

${CURDIR}/batch-opt-pass.py -k $KERNEL_PATH -o $DRVMOD_PATH/$BUSCLASS/libBusClassPass.so -p $BUSCLASS -n $(nproc) | tee $OUTPUT_PATH/busclass.raw

cat $OUTPUT_PATH/busclass.raw | grep '^bus: ' | sort | uniq > $OUTPUT_PATH/busdrv.raw
cat $OUTPUT_PATH/busclass.raw | grep '^class: ' | sort | uniq > $OUTPUT_PATH/classdrv.raw
cat $OUTPUT_PATH/busdrv.raw | awk '{ print $3 }' | sort | uniq > $OUTPUT_PATH/busdrv.names
cat $OUTPUT_PATH/classdrv.raw | awk '{ print $3 }' | sort | uniq > $OUTPUT_PATH/classdrv.names

${CURDIR}/batch-opt-pass.py -k $KERNEL_PATH -o $DRVMOD_PATH/$DRVDEV/libDrvDevRegPass.so -p $DRVDEV -b $OUTPUT_PATH/busdrv.names -n $(nproc) | tee $OUTPUT_PATH/bus-regfuns.raw
${CURDIR}/batch-opt-pass.py -k $KERNEL_PATH -o $DRVMOD_PATH/$DRVDEV/libDrvDevRegPass.so -p $DRVDEV -b $OUTPUT_PATH/classdrv.names -n $(nproc) | tee $OUTPUT_PATH/class-regfuns.raw

LINUX_PREFIX="^\/.*linux-[0-9]\+\.[0-9]\+\.[0-9]\+\/"
HACKSAW_SUFFIX="\.hacksaw\.bc "

cat $OUTPUT_PATH/bus-regfuns.raw | grep '^bus: ' | awk '{ print $2,$3 }' | sed "s/$LINUX_PREFIX//" | sed "s/$HACKSAW_SUFFIX/ /" | sort | uniq > $OUTPUT_PATH/bus-regfuns.db
cat $OUTPUT_PATH/class-regfuns.raw | grep '^class: ' | awk '{ print $2,$3 }' | sed "s/$LINUX_PREFIX//" | sed "s/$HACKSAW_SUFFIX/ /" | sort | uniq > $OUTPUT_PATH/class-regfuns.db

cat $OUTPUT_PATH/builtin-objs.raw | sed "s/$LINUX_PREFIX//" | sort | uniq > $OUTPUT_PATH/builtin-objs.db
