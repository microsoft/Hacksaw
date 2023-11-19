#!/bin/bash
if [ $# -eq 2 ] || [ $# -eq 3 ]; then
  KERNEL_VER="$1"
  TARGET_CONFIG_FILE=$(realpath $2)
  if [ $# -eq 3 ]; then
    NOINLINE="$3"
  fi
else
  echo "Usage: $0 <KERNEL_VER> <CONFIG_FILE> [NOINLINE]"
  exit 1
fi

if [ ! -e "$TARGET_CONFIG_FILE" ]; then
  echo "$TARGET_CONFIG_FILE does not exist."
  exit 1
fi

CURDIR=$(dirname $(realpath $0))
ROOTDIR=$(dirname ${CURDIR})
SRCDIR="$CURDIR/src"
BUILDDIR="${ROOTDIR}/build/"

KERNEL_SRC_PATH="$SRCDIR/linux-$KERNEL_VER/"
KERNEL_TARGET_BUILD_PATH="$BUILDDIR/linux-$KERNEL_VER-target/"
KERNEL_NOINLINE_BUILD_PATH="$BUILDDIR/linux-$KERNEL_VER-noinline/"

KERNEL_CONF_FRAGMENT="/tmp/temp.kconfig.fragment"
cat "${CURDIR}/hacksaw.kconfig.fragment" "${CURDIR}/nosig.kconfig.fragment" | sort | uniq > $KERNEL_CONF_FRAGMENT

mkdir -p $SRCDIR
mkdir -p $KERNEL_TARGET_BUILD_PATH
mkdir -p $KERNEL_NOINLINE_BUILD_PATH

if [ ! -d "$KERNEL_SRC_PATH" ]; then
  wget -c https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VER:0:1}.x/linux-$KERNEL_VER.tar.xz -O - | tar -xJ -C $SRCDIR
fi
if [ "${KERNEL_VER:0:1}" -lt "5" ] || [ "${KERNEL_VER:0:1}" = "5" ] && [ "${KERNEL_VER:2:2}" -le "15" ]; then
#  https://lore.kernel.org/r/20211104215047.663411-1-nathan@kernel.org/
  sed -i 's/1E6L/USEC_PER_SEC/g' $KERNEL_SRC_PATH/drivers/power/reset/ltc2952-poweroff.c
#  https://lore.kernel.org/r/20211104215923.719785-1-nathan@kernel.org/
  sed -i 's/1E6L/USEC_PER_SEC/g' $KERNEL_SRC_PATH/drivers/usb/dwc2/hcd_queue.c
# gcc sanitizer bug
  sed -i 's/-Wall//g' $KERNEL_SRC_PATH/tools/lib/subcmd/Makefile
# TODO: use patch instead of sed
fi

pushd $KERNEL_SRC_PATH

make mrproper
cp $TARGET_CONFIG_FILE $KERNEL_TARGET_BUILD_PATH/.config
./scripts/kconfig/merge_config.sh -O $KERNEL_TARGET_BUILD_PATH $KERNEL_TARGET_BUILD_PATH/.config $KERNEL_CONF_FRAGMENT
make CC=clang olddefconfig O=$KERNEL_TARGET_BUILD_PATH
make CC=clang -j$(nproc) KCFLAGS='-w' vmlinux modules O=$KERNEL_TARGET_BUILD_PATH

if [ ! -z "$NOINLINE" ]; then
  make mrproper
  cp $TARGET_CONFIG_FILE $KERNEL_NOINLINE_BUILD_PATH/.config
  ./scripts/kconfig/merge_config.sh -O $KERNEL_NOINLINE_BUILD_PATH $KERNEL_BUILD_PATH/.config $KERNEL_CONF_FRAGMENT
  make CC=clang olddefconfig O=$KERNEL_NOINLINE_BUILD_PATH
  make CC=clang -j$(nproc) KCFLAGS='-w -fno-inline-functions -fno-inline-small-functions -fno-inline-functions-called-once -U__OPTIMIZE__' vmlinux modules O=$KERNEL_NOINLINE_BUILD_PATH
fi

popd

rm -f $KERNEL_CONF_FRAGMENT

${CURDIR}/buildir.py $KERNEL_TARGET_BUILD_PATH
if [ ! -z "$NOINLINE" ]; then
  ${CURDIR}/buildir.py $KERNEL_NOINLINE_BUILD_PATH
fi
