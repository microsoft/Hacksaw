#!/bin/bash
USERID=$(id -u)
GROUPID=$(id -g)

pushd docker
./build-containers.sh
popd

HWPROFILE="dataset/hwenv/qemu-kvm5.txt"

SYSIMG="mantic-server-cloudimg-amd64.img"
IMGURL="https://cloud-images.ubuntu.com/mantic/20231014/${SYSIMG}"

if [ ! -e "$SYSIMG" ]; then
  wget $IMGURL
fi

CURDIR=$(dirname $(realpath $0))
BUILDDIR="${CURDIR}/build/"
IMAGE_ROOT="${CURDIR}/out/out.${SYSIMG}"

# extract kernel, modules, initramfs, and config from a target system image
if [ ! -e $IMAGE_ROOT ]; then
  docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID \
    --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
    --group-add $(getent group kvm | cut -d: -f3) \
    --name hacksaw-imager hacksaw-imager:0.1 \
    -- \
    extract -i $SYSIMG -o ${CURDIR}/out
fi

KERNEL_VER=$(${CURDIR}/utils/get-kernel-info.sh $IMAGE_ROOT | grep 'version:' | awk '{ print $2 }')
CONFIG_FILE=$(${CURDIR}/utils/get-kernel-info.sh $IMAGE_ROOT | grep 'config:' | awk '{ print $2 }')

if [ "$KERNEL_VER" = "none" ]; then
  echo "Failed to identify kernel version"
  exit 1
fi

if [ "$CONFIG_FILE" = "none" ]; then
  echo "Failed to get a kernel configuration file"
  exit 1
fi

OUTPUT_PATH="${CURDIR}/out/${KERNEL_VER}"
KERNEL_BUILD_PATH="${BUILDDIR}/linux-${KERNEL_VER}-target/"

# prepare database for target kernel version
if [ ! -e $OUTPUT_PATH ]; then
  docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
    -- \
    prepare -k $KERNEL_VER
fi

# analyze target kernel based on its version, its build configuration, and prepared database
if [ ! -e $KERNEL_BUILD_PATH ]; then
  docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
    -- \
    analyze -k $KERNEL_VER -c $CONFIG_FILE
fi

# patch extracted kernel, modules, and initramfs
docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
  -- \
  patch -k $KERNEL_VER -i $IMAGE_ROOT -p $HWPROFILE

# update the target image using patched files
docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID \
  --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
  --group-add $(getent group kvm | cut -d: -f3) \
  --name hacksaw-imager hacksaw-imager:0.1 \
  -- \
  update -i $SYSIMG -p $IMAGE_ROOT
