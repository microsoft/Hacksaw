#!/bin/bash

usage() {
  echo "Usage: hacksaw update -i <system image path> -p <patched kernel files path>" 1>&2
  exit 1
}

while getopts ":i:p:" o; do
  case "${o}" in
    i)
      sysimg=${OPTARG}
      ;;
    p)
      patchpath=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

if [ -z "${sysimg}" ] || [ -z "${patchpath}" ]; then
  usage
fi

ROOTDIR=$(dirname $(realpath $0))/hacksaw
IMAGE=${ROOTDIR}/${sysimg}
IMAGEIN=${ROOTDIR}/${patchpath}
MNTPOINT="/tmp/mnt/"

if [ ! -e "$IMAGE" ]; then
  echo "$IMAGE does not exist."
  exit 1
fi

if [ ! -e "$IMAGEIN" ]; then
  echo "$IMAGEIN does not exist."
  exit 1
fi

mkdir -p $MNTPOINT
guestmount -a $IMAGE -i --rw $MNTPOINT
rm -rf $MNTPOINT/lib/modules/*
cp $IMAGEIN/boot/vmlinuz* $MNTPOINT/boot/
cp $IMAGEIN/boot/initr* $MNTPOINT/boot/
cp -a $IMAGEIN/lib/modules/* $MNTPOINT/lib/modules/
chmod 755 $MNTPOINT/boot/vmlinuz*
chmod 755 $MNTPOINT/boot/initr*
chmod -R 755 $MNTPOINT/lib/modules/*
umount $MNTPOINT

echo 'System image is updated.'
