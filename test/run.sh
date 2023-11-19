#!/bin/bash
usage() {
  echo "Usage: $0 -i <system image path> -p <hardware profile file> [-s <system.map file>]" 1>&2
  exit 1
}

while getopts ":i:p:s:" o; do
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

BLUE='\033[0;34m'
NC='\033[0m'

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

pushd ${ROOTDIR}/docker
./build-containers.sh
popd

BUILDDIR="${ROOTDIR}/build/"
IMAGE_BASE_PATH="out/out.${SYSIMG}"

# extract kernel, modules, initramfs, and config from a target system image
if [ ! -e ${ROOTDIR}/${IMAGE_BASE_PATH} ]; then
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

echo -e "${BLUE}System image: ${SYSIMG}${NC}"
echo -e "${BLUE}Kernel version: ${KERNEL_VER}${NC}"
echo -e "${BLUE}Config file: ${CONFIG_FILE}${NC}"

OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}"
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
