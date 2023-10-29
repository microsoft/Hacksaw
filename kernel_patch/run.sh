#!/bin/bash

# Run in ROOT on HOST env (??!! ikr):
# apt install -y build-essential libncurses-dev bison flex \
#    libssl-dev libelf-dev make cmake file bc cpio kmod \
#    guestmount git zstd gzip bzip2 xz-utils lz4 lzop dwarves
# pip3 install psutil capstone pyelftools

KERN_SRC=$(realpath "$1")
DATASET_DIR=$(realpath "$2")
ARGS="${@:2}"
KERN_BUILD="${KERN_SRC}/build_llvm"
curdir=$(dirname $(realpath $0))
OUTPUT_DIR=$(dirname ${curdir})/out
KERNELRELEASE=$(cat ${KERN_SRC}/build_llvm/include/config/kernel.release 2> /dev/null)

# Drop '-t' to patch kernel/images
${curdir}/runfilter.py -k ${KERN_SRC} \
    -b ${KERN_BUILD} \
    -P ${DATASET_DIR} \
    -p ${OUTPUT_DIR} \
    -o ${OUTPUT_DIR} \
    ${ARGS}
