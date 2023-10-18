#!/bin/bash
set -e

OUTPUT_PATH="out/"
BUILD_PATH="build/"

KERNEL_VER="5.19.17"
KERNEL_PATH="$BUILD_PATH/linux-$KERNEL_VER/"
KERNEL_CONF="wllvm.config"

BUSCLASS="busclass"
DRVDEV="drvdevreg"
BUSCLASS_SRC=$(realpath "llvm-pass-$BUSCLASS/")
DRVDEV_SRC=$(realpath "llvm-pass-$DRVDEV/")

mkdir -p $OUTPUT_PATH
mkdir -p $BUILD_PATH

if [ ! -d "$KERNEL_PATH" ]; then
  pushd $BUILD_PATH
  wget -c https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-$KERNEL_VER.tar.xz -O - | tar -xJ
  popd
fi
 
cp $KERNEL_CONF $KERNEL_PATH/.config
 
pushd $KERNEL_PATH
export LLVM_COMPILER=clang
make CC=wllvm olddefconfig
make CC=wllvm -j$(nproc)
popd

mkdir -p $BUILD_PATH/$BUSCLASS
mkdir -p $BUILD_PATH/$DRVDEV

pushd $BUILD_PATH/$BUSCLASS
cmake $BUSCLASS_SRC
make
popd

pushd $BUILD_PATH/$DRVDEV
cmake $DRVDEV_SRC
make
popd

./extract-kernel-bc.py -k $KERNEL_PATH -n $(nproc)
rm $KERNEL_PATH/vmlinux.o.hacksaw.bc

./batch-opt-pass.py -k $KERNEL_PATH -o $BUILD_PATH/$BUSCLASS/$BUSCLASS/libBusClassPass.so -p $BUSCLASS -n $(nproc)
find $KERNEL_PATH -name "*.hacksaw.bc.out" -exec cat {} \; | tee $OUTPUT_PATH/busclass.out
find $KERNEL_PATH -name "*.hacksaw.bc.out" -exec rm -f {} \;

cat $OUTPUT_PATH/busclass.out | grep '^bus: ' | sort | uniq > $OUTPUT_PATH/busdrv.db
cat $OUTPUT_PATH/busclass.out | grep '^class: ' | sort | uniq > $OUTPUT_PATH/classdrv.db
cat $OUTPUT_PATH/busdrv.db | awk '{ print $3 }' | sort | uniq > $OUTPUT_PATH/busdrv.list
cat $OUTPUT_PATH/classdrv.db | awk '{ print $3 }' | sort | uniq > $OUTPUT_PATH/classdrv.list

./batch-opt-pass.py -k $KERNEL_PATH -o $BUILD_PATH/$DRVDEV/$DRVDEV/libDrvDevRegPass.so -p $DRVDEV -l $OUTPUT_PATH/busdrv.list -n $(nproc)
find $KERNEL_PATH -name "*.hacksaw.bc.out" -exec cat {} \; | tee $OUTPUT_PATH/bus-regfuns.out
find $KERNEL_PATH -name "*.hacksaw.bc.out" -exec rm -f {} \;

./batch-opt-pass.py -k $KERNEL_PATH -o $BUILD_PATH/$DRVDEV/$DRVDEV/libDrvDevRegPass.so -p $DRVDEV -l $OUTPUT_PATH/classdrv.list -n $(nproc)
find $KERNEL_PATH -name "*.hacksaw.bc.out" -exec cat {} \; | tee $OUTPUT_PATH/class-regfuns.out
find $KERNEL_PATH -name "*.hacksaw.bc.out" -exec rm -f {} \;

cat $OUTPUT_PATH/bus-regfuns.out | grep '^bus: ' | awk '{ print $2,$3 }' |
  sort | uniq > $OUTPUT_PATH/bus-regfuns.txt
cat $OUTPUT_PATH/class-regfuns.out | grep '^class: ' | awk '{ print $2,$3 }' |
  sort | uniq > $OUTPUT_PATH/class-regfuns.txt
