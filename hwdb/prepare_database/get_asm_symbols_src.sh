#!/bin/bash

CURDIR=$(dirname $(realpath $0))
KERNEL_SRC_PATH=$(realpath "$1")
OUTPUT_PATH=$(realpath "$2")

find $KERNEL_SRC_PATH -name "*.S" -exec cat {} \; | grep "^EXPORT_SYMBOL" | sed "s/^EXPORT_SYMBOL.*(//" | sed "s/).*$//" | sed "/#/d" | sort | uniq > ${OUTPUT_PATH}/asmsym.list
