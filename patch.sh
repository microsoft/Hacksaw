#!/bin/bash

KERNEL_VER="5.19.17"
KERN_SRC=$(dirname $(realpath "$0"))/build/linux-${KERNEL_VER}
DATASET_DIR=$(realpath "$1")

./kernel_patch/run.sh ${KERN_SRC} ${DATASET_DIR} -n 8
