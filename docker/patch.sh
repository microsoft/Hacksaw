#!/bin/bash

usage() {
  echo "Usage: hacksaw patch -k <kernel version> -i <system image path> -p <hardware profile file> [-s <system.map file>]" 1>&2
  exit 1
}

while getopts ":k:i:p:s:" o; do
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
    s)
      sysmap=${OPTARG}
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

if [ ! -e ${sysimg} ]; then
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

ROOTDIR=$(dirname $(realpath $0))/hacksaw
BUILDDIR="${ROOTDIR}/build/"
OUTPUT_PATH="${ROOTDIR}/out/${kerver}/"
KERNEL_SRC_PATH="${ROOTDIR}/kernel/src/linux-${kerver}/"
KERNEL_BUILD_PATH="$BUILDDIR/linux-${kerver}-target/"

if [ -z "${sysmap}" ]; then
${ROOTDIR}/kernel_patch/patch-disk-image.py -k ${KERNEL_SRC_PATH} -b ${KERNEL_BUILD_PATH} -d ${OUTPUT_PATH} -o ${OUTPUT_PATH} \
  -i $sysimg -p $profile
else
${ROOTDIR}/kernel_patch/patch-disk-image.py -k ${KERNEL_SRC_PATH} -b ${KERNEL_BUILD_PATH} -d ${OUTPUT_PATH} -o ${OUTPUT_PATH} \
  -i $sysimg -p $profile -s $sysmap
fi

echo 'System image patching is done.'
