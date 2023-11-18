#!/bin/bash
USERID=$(id -u)
GROUPID=$(id -g)

BASEDIR=$(dirname $(dirname $(realpath $0)))
CNT_BASE_PATH="/hacksaw"

pushd $BASEDIR

pushd docker
./build-containers.sh
popd

HWPROFILE="test/hwprof/qemu-kvm.txt"

SYSIMG="mantic-server-cloudimg-amd64.img"
IMGURL="https://cloud-images.ubuntu.com/mantic/current/${SYSIMG}"
# SYSIMG="openSUSE-Leap-15.5.x86_64-NoCloud.qcow2"
# IMGURL="https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.5/images/${SYSIMG}"

SYSIMG_PATH="test/images/${SYSIMG}"
if [ ! -e ${BASEDIR}/${SYSIMG_PATH} ]; then
  mkdir -p $(dirname ${BASEDIR}/${SYSIMG_PATH})
  wget $IMGURL -O ${BASEDIR}/${SYSIMG_PATH}
fi

BUILDDIR="${BASEDIR}/build/"
IMAGE_BASE_PATH="out/out.${SYSIMG}"

# extract kernel, modules, initramfs, and config from a target system image
if [ ! -e ${BASEDIR}/${IMAGE_BASE_PATH} ]; then
  docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID \
    --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
    --group-add $(getent group kvm | cut -d: -f3) \
    --name hacksaw-imager hacksaw-imager:0.1 \
    -- \
    extract -i $SYSIMG_PATH -o out/
fi

KERNEL_VER=$(${BASEDIR}/utils/get-kernel-info.sh $IMAGE_BASE_PATH | grep 'version:' | awk '{ print $2 }')
CONFIG_FILE=$(${BASEDIR}/utils/get-kernel-info.sh $IMAGE_BASE_PATH | grep 'config:' | awk '{ print $2 }')

if [ "$KERNEL_VER" = "none" ]; then
  echo "Failed to identify kernel version"
  exit 1
fi

if [ "$CONFIG_FILE" = "none" ]; then
  echo "Failed to get a kernel configuration file"
  exit 1
fi

echo "System image: $SYSIMG"
echo "Kernel version: $KERNEL_VER"
echo "Config file: $CONFIG_FILE"

OUTPUT_PATH="${BASEDIR}/out/${KERNEL_VER}"
KERNEL_BUILD_PATH="${BUILDDIR}/linux-${KERNEL_VER}-target/"

# prepare database for target kernel version
if [ ! -e $OUTPUT_PATH ]; then
  docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
    -- \
    prepare -k $KERNEL_VER
fi

# analyze target kernel based on its version, its build configuration, and prepared database
if [ ! -e $KERNEL_BUILD_PATH ]; then
  docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
    -- \
    analyze -k $KERNEL_VER -c $CONFIG_FILE
fi

# patch extracted kernel, modules, and initramfs
docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
  -- \
  patch -k $KERNEL_VER -i $IMAGE_BASE_PATH -p $HWPROFILE

# update the target image using patched files
docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID \
  --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
  --group-add $(getent group kvm | cut -d: -f3) \
  --name hacksaw-imager hacksaw-imager:0.1 \
  -- \
  update -i $SYSIMG_PATH -p $IMAGE_BASE_PATH

popd
