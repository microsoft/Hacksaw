#!/bin/bash

usage() {
  echo "Usage: hacksaw patch -i <system image path> -p <hardware profile file>" 1>&2
  exit 1
}

while getopts ":i:c:" o; do
  case "${o}" in
    i)
      sysimg=${OPTARG}
      ;;
    p)
      profile=${OPTARG}
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

ROOTDIR=$(dirname $(realpath $0))/hacksaw
BUILDDIR="${ROOTDIR}/build/"
OUTPUT_PATH="${ROOTDIR}/out/${KERNEL_VER}/"
KERNEL_SRC_PATH="${ROOTDIR}/kernel/src/linux-${KERNEL_VER}/"
KERNEL_BUILD_PATH="$BUILDDIR/linux-${KERNEL_VER}-target/"

${ROOTDIR}/kernel_patch/patch-disk-image.py -k ${KERNEL_SRC_PATH} -b ${KERNEL_BUILD_PATH} -d ${OUTPUT_PATH} -o ${OUTPUT_PATH} \
  -i $sysimg -p $profile

echo 'System image patching is done.'
