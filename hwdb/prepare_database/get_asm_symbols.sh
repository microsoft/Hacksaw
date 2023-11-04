#!/bin/bash

CURDIR=$(dirname $(realpath $0))
KERNEL_SRC_PATH=$(realpath "$1")
KERNEL_BUILD_PATH=$(realpath "$2")

ASM_FILES=$(find $KERNEL_SRC_PATH -name '*.S')

if [ ! -z "$ASM_FILES" ]; then
    while IFS= read -r line; do
        tempobj=$(echo "$line" | sed "s/\.S$/.o/")
        relobj=$(realpath --relative-to=$KERNEL_SRC_PATH $tempobj)
        finobj="$KERNEL_BUILD_PATH/$relobj"
        if [ -e "$finobj" ]; then
            nm $finobj | grep ' [T|t|W|w] ' > ${finobj}.asmsym
        fi
    done <<< "$ASM_FILES"
fi
