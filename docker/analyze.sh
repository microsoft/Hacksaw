#!/bin/bash

usage() {
  echo "Usage: hacksaw analyze -k <kernel version> -c <kernel configuration file>" 1>&2
  exit 1
}

while getopts ":k:c:" o; do
  case "${o}" in
    k)
      kerver=${OPTARG}
      ;;
    c)
      confpath=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

if [ -z "${kerver}" ] || [ -z "${confpath}" ]; then
  usage
fi

ROOTDIR=$(dirname $(realpath $0))/hacksaw

${ROOTDIR}/kernel_patch/get-target-objdep.sh $kerver ${ROOTDIR}/${confpath}

echo 'Dependency analyze is done.'
