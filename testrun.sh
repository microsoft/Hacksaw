#!/bin/bash
USERID=$(id -u)
GROUPID=$(id -g)

pushd docker
./build-containers.sh
popd

SYSIMG="debian-12-generic-amd64-20231013-1532.qcow2"
IMGURL="https://cloud.debian.org/images/cloud/bookworm/20231013-1532/${SYSIMG}"

if [ ! -e "$SYSIMG" ]; then
  wget $IMGURL
fi

KERNEL_VER="6.1"
CURDIR=$(dirname $(realpath $0))
BUILDDIR="${CURDIR}/build/"
OUTPUT_PATH="${CURDIR}/out/${KERNEL_VER}"
KERNEL_BUILD_PATH="$BUILDDIR/linux-${KERNEL_VER}-target/"

if [ ! -e "$OUTPUT_PATH" ]; then
  docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
    -- \
    prepare -k 6.1
fi

if [ ! -e "${CURDIR}/out/out.${SYSIMG}" ]; then
  docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID \
    --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
    --group-add $(getent group kvm | cut -d: -f3) \
    --name hacksaw-imager hacksaw-imager:0.1 \
    -- \
    extract -i ${SYSIMG} -o out
fi

if [ ! -e "$KERNEL_BUILD_PATH" ]; then
  docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID --name hacksaw hacksaw:0.1 \
    -- \
    analyze -k 6.1 -c out/out.${SYSIMG}/boot/config-6.1.0-13-amd64

fi

docker run -it --rm -v $PWD:/hacksaw -u $USERID:$GROUPID \
  --cap-add SYS_ADMIN --device /dev/fuse --device /dev/kvm --security-opt apparmor:unconfined \
  --group-add $(getent group kvm | cut -d: -f3) \
  --name hacksaw-imager hacksaw-imager:0.1 \
  -- \
  update -i ${SYSIMG} -p out/out.${SYSIMG}
