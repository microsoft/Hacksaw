#!/bin/bash

if [ $# -eq 2 ]; then
  KERNEL_VER="$1"
  CONFIG_FILE=$(realpath $2)
else
  echo "Usage: $0 <KERNEL_VER> <CONFIG_FILE>"
  exit 1
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
SRCDIR="$CURDIR/src"
BUILDDIR="${ROOTDIR}/build/"

KERNEL_SRC_PATH="$SRCDIR/linux-$KERNEL_VER/"
KERNEL_BUILD_BZIMAGE_PATH="$BUILDDIR/linux-$KERNEL_VER-bzimage/"

KERNEL_CONF_FRAGMENT="${CURDIR}/nosig.kconfig.fragment"

mkdir -p $SRCDIR
mkdir -p $KERNEL_BUILD_BZIMAGE_PATH

if [ ! -d "$KERNEL_SRC_PATH" ]; then
  wget -c https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VER:0:1}.x/linux-$KERNEL_VER.tar.xz -O - | tar -xJ -C $SRCDIR
fi
sed -i 's/-Wall//g' $KERNEL_SRC_PATH/tools/lib/subcmd/Makefile # bypass a gcc sanitizer bug

pushd $KERNEL_SRC_PATH

make mrproper
cp $CONFIG_FILE $KERNEL_BUILD_BZIMAGE_PATH/.config
./scripts/kconfig/merge_config.sh -O $KERNEL_BUILD_BZIMAGE_PATH $KERNEL_BUILD_BZIMAGE_PATH/.config $KERNEL_CONF_FRAGMENT
make olddefconfig O=$KERNEL_BUILD_BZIMAGE_PATH
make -j$(nproc) bzImage O=$KERNEL_BUILD_BZIMAGE_PATH

popd
