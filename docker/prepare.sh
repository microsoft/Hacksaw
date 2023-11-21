#!/bin/bash

usage() {
  echo "Usage: hacksaw prepare -k <kernel version> [-c <kernel configuration file>]" 1>&2
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

if [ -z "${kerver}" ]; then
  usage
fi

if [ ! -z "${confpath}" ] && [ ! -f "${confpath}" ]; then
  echo "$confpath does not exist."
  exit 1
fi

ROOTDIR=$(dirname $(realpath $0))/hacksaw

if [ -z "${confpath}" ]; then
  ${ROOTDIR}/kernel/prepare_kernel.sh $kerver
else
  ${ROOTDIR}/kernel/prepare_kernel.sh $kerver $confpath
fi
${ROOTDIR}/hwdb/gendb.sh $kerver &
${ROOTDIR}/driver_model/do-driver-model.sh $kerver &
${ROOTDIR}/comp_unit/do-comp-unit.sh $kerver &

while true
do
  if [ -f /tmp/hw.done ]; then
    if [ -f /tmp/drvmod.done ]; then
      if [ -f /tmp/compunit.done ]; then
        break
      fi
    fi
  fi
  sleep 5
done

echo 'Database is prepared.'
