#!/bin/bash

usage() {
  echo "Usage: hacksaw extract -i <system image path> -o <output path>" 1>&2
  exit 1
}

while getopts ":i:o:" o; do
  case "${o}" in
    i)
      sysimg=${OPTARG}
      ;;
    o)
      outpath=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

if [ -z "${sysimg}" ] || [ -z "${outpath}" ]; then
  usage
fi

ROOTDIR=$(dirname $(realpath $0))/hacksaw
IMAGE=${ROOTDIR}/${sysimg}
IMAGEOUT="${outpath}/out.$(basename ${sysimg})"
MNTPOINT="/tmp/mnt/"

if [ ! -e "$IMAGE" ]; then
  echo "$IMAGE does not exist."
  exit 1
fi

mkdir -p $IMAGEOUT $IMAGEOUT/lib $MNTPOINT
guestmount -a $IMAGE -i --ro $MNTPOINT
cp -a $MNTPOINT/boot $IMAGEOUT
cp -a $MNTPOINT/lib/modules $IMAGEOUT/lib
umount $MNTPOINT

echo 'System image is extracted.'
