#!/bin/bash
usage() {
  echo "Usage: $0 -i <system image path> -p <hardware profile file> [-s <system.map file>] [-b 1 (build container)] [-c 1 (use in-image config)]" 1>&2
  exit 1
}

while getopts ":i:p:s:b:c:" o; do
  case "${o}" in
    i)
      sysimg=${OPTARG}
      ;;
    p)
      profile=${OPTARG}
      ;;
    s)
      sysmap=${OPTARG}
      ;;
    b)
      build=${OPTARG}
      ;;
    c)
      imgconf=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

if [ -z "${sysimg}" ] || [ -z "${profile}" ]; then
  usage
fi

if [ ! -f ${sysimg} ]; then
  echo "$sysimg does not exist."
  exit 1
fi

if [ ! -f ${profile} ]; then
  echo "$profile does not exist."
  exit 1
fi

if [ ! -z "${sysmap}" ] && [ ! -f ${sysmap} ]; then
  echo "$sysmap does not exist."
  exit 1
fi

USERID=$(id -u)
GROUPID=$(id -g)

ROOTDIR=$(dirname $(dirname $(realpath $0)))
CNT_BASE_PATH="/hacksaw"

HWPROFILE=$(realpath --relative-to=$ROOTDIR $profile)
SYSIMG_PATH=$(realpath --relative-to=$ROOTDIR $sysimg)
SYSIMG=$(basename $SYSIMG_PATH)
if [ -z "${sysmap}" ]; then
  SYSMAP_PATH=""
else
  SYSMAP_PATH=$(realpath --relative-to=$ROOTDIR $sysmap)
fi

pushd ${ROOTDIR}

if [ ! -z "${build}" ]; then
  pushd ${ROOTDIR}/docker
  ./build-containers.sh
  popd
fi

BUILDDIR="${ROOTDIR}/build/"
IMAGE_BASE_PATH="out/${SYSIMG}.extracted"

# extract kernel, modules, initramfs, and config from a target system image
if [ ! -d ${ROOTDIR}/${IMAGE_BASE_PATH} ]; then
  docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID \
    --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
    --group-add $(getent group kvm | cut -d: -f3) \
    --name hacksaw-imager hacksaw-imager:0.1 \
    -- \
    extract -i $SYSIMG_PATH -o out/
fi

KERNEL_VER=$(${ROOTDIR}/utils/get-kernel-info.sh ${IMAGE_BASE_PATH} | grep 'version:' | awk '{ print $2 }')
CONFIG_FILE=$(${ROOTDIR}/utils/get-kernel-info.sh ${IMAGE_BASE_PATH} | grep 'config:' | awk '{ print $2 }')

if [ "$KERNEL_VER" = "none" ]; then
  echo "Failed to identify kernel version"
  exit 1
fi

if [ "$CONFIG_FILE" = "none" ]; then
  echo "Failed to get a kernel configuration file"
  exit 1
fi

echo "System image: ${SYSIMG}"
echo "Kernel version: ${KERNEL_VER}"
echo "Config file: ${CONFIG_FILE}"

OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"
KERNEL_BUILD_PATH="${BUILDDIR}/linux-${KERNEL_VER}-target/"

# prepare database for target kernel version
if [ ! -d $OUTPUT_PATH ] || [ ! -f ${OUTPUT_PATH}/builtin-objs.dep ] || [ ! -f ${OUTPUT_PATH}/bus-regfuns.db ] || [ ! -f ${OUTPUT_PATH}/class-regfuns.db ] || [ ! -f ${OUTPUT_PATH}/hw.db ]; then
  if [ -z $imgconf ]; then
    docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
      -- \
      prepare -k $KERNEL_VER
  else
    docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
      -- \
      prepare -k $KERNEL_VER -c $CONFIG_FILE
  fi
fi

# analyze target kernel based on its version, its build configuration, and prepared database
if [ ! -e $KERNEL_BUILD_PATH ] || [ ! -e ${KERNEL_BUILD_PATH}/kernel/entry/common.o.impnoin ] ; then
  docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
    -- \
    analyze -k $KERNEL_VER -c $CONFIG_FILE
fi

# patch extracted kernel, modules, and initramfs
if [ "$SYSMAP_PATH" = "" ]; then
docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
  -- \
  patch -k $KERNEL_VER -i $IMAGE_BASE_PATH -p $HWPROFILE
else
docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
  -- \
  patch -k $KERNEL_VER -i $IMAGE_BASE_PATH -p $HWPROFILE -s $SYSMAP_PATH
fi

# update the target image using patched files
docker run -it --rm -v $PWD:$CNT_BASE_PATH -u $USERID:$GROUPID \
  --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
  --group-add $(getent group kvm | cut -d: -f3) \
  --name hacksaw-imager hacksaw-imager:0.1 \
  -- \
  update -i $SYSIMG_PATH -p $IMAGE_BASE_PATH

popd
