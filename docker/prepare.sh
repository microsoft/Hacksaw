#!/bin/bash

usage() {
  echo "Usage: hacksaw prepare -k <kernel version>" 1>&2
  exit 1
}

while getopts ":k:" o; do
  case "${o}" in
    k)
      kerver=${OPTARG}
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

ROOTDIR=$(dirname $(realpath $0))/hacksaw

${ROOTDIR}/kernel/prepare_kernel.sh $kerver
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
