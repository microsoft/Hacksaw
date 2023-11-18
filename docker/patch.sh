#!/bin/bash

usage() {
  echo "Usage: hacksaw patch -k <kernel version> -i <system image path> -p <hardware profile file>" 1>&2
  exit 1
}

while getopts ":k:i:p:" o; do
  case "${o}" in
    k)
      kerver=${OPTARG}
      ;;
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

if [ -z "${kerver}" ] || [ -z "${sysimg}" ] || [ -z "${profile}" ]; then
  usage
fi

ROOTDIR=$(dirname $(realpath $0))/hacksaw
BUILDDIR="${ROOTDIR}/build/"
OUTPUT_PATH="${ROOTDIR}/out/${kerver}/"
KERNEL_SRC_PATH="${ROOTDIR}/kernel/src/linux-${kerver}/"
KERNEL_BUILD_PATH="$BUILDDIR/linux-${kerver}-target/"

${ROOTDIR}/kernel_patch/patch-disk-image.py -k ${KERNEL_SRC_PATH} -b ${KERNEL_BUILD_PATH} -d ${OUTPUT_PATH} -o ${OUTPUT_PATH} \
  -i $sysimg -p $profile

echo 'System image patching is done.'
