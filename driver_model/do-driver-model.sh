#!/bin/bash

if [ $# -eq 1 ]; then
  KERNEL_VER="$1"
else
  KERNEL_VER="5.19.17"
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
BUILDDIR="${ROOTDIR}/build/"
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"

KERNEL_BUILD_PATH="$BUILDDIR/linux-$KERNEL_VER/"

BUSCLASS="busclass"
DRVDEV="drvdevreg"
DRVMOD_SRC_PATH=$(realpath "${CURDIR}/llvm-pass")
DRVMOD_BUILD_PATH="$BUILDDIR/drvmod"

if [ ! -d "$KERNEL_BUILD_PATH" ]; then
  echo "Linux kernel in LLVM bitcode is required. Run /kernel/prepare_kernel.sh $KERNEL_VER first"
  exit 1
fi

mkdir -p $DRVMOD_BUILD_PATH
pushd $DRVMOD_BUILD_PATH
cmake $DRVMOD_SRC_PATH
make -j$(nproc)
popd

mkdir -p $OUTPUT_PATH

${CURDIR}/batch-opt-pass.py -k $KERNEL_BUILD_PATH -o $DRVMOD_BUILD_PATH/$BUSCLASS/libBusClassPass.so -p $BUSCLASS -n $(nproc) | tee $OUTPUT_PATH/busclass.raw

cat $OUTPUT_PATH/busclass.raw | grep -a '^bus: ' | sort | uniq > $OUTPUT_PATH/busdrv.raw
cat $OUTPUT_PATH/busclass.raw | grep -a '^class: ' | sort | uniq > $OUTPUT_PATH/classdrv.raw
cat $OUTPUT_PATH/busdrv.raw | awk '{ print $3 }' | sort | uniq > $OUTPUT_PATH/busdrv.names
cat $OUTPUT_PATH/classdrv.raw | awk '{ print $3 }' | sort | uniq > $OUTPUT_PATH/classdrv.names

${CURDIR}/batch-opt-pass.py -k $KERNEL_BUILD_PATH -o $DRVMOD_BUILD_PATH/$DRVDEV/libDrvDevRegPass.so -p $DRVDEV -b $OUTPUT_PATH/busdrv.names -n $(nproc) | tee $OUTPUT_PATH/bus-regfuns.raw
${CURDIR}/batch-opt-pass.py -k $KERNEL_BUILD_PATH/ -o $DRVMOD_BUILD_PATH/$DRVDEV/libDrvDevRegPass.so -p $DRVDEV -b $OUTPUT_PATH/classdrv.names -n $(nproc) | tee $OUTPUT_PATH/class-regfuns.raw

LINUX_PREFIX="^\/.*linux-[0-9]\+\.[0-9]\+\(\|\.[0-9]\+\)\/"

cat $OUTPUT_PATH/bus-regfuns.raw | grep -a '^bus: ' | awk '{ print $2,$3 }' | sed "s/$LINUX_PREFIX//" | sort | uniq | $CURDIR/uniq-funcs.py | sort > $OUTPUT_PATH/bus-regfuns.db
cat $OUTPUT_PATH/class-regfuns.raw | grep -a '^class: ' | awk '{ print $2,$3 }' | sed "s/$LINUX_PREFIX//" | sort | uniq | $CURDIR/uniq-funcs.py | sort > $OUTPUT_PATH/class-regfuns.db

touch /tmp/drvmod.done
