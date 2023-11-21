#!/bin/bash
# *.imptab -> *.impnoin

curdir=$(dirname $(realpath $0))
linux_noinline_build=$(realpath "$1")
linux_target_build=$(realpath "$2")

prefix_len=${#linux_noinline_build}
for f in `find $linux_noinline_build -name "*.imptab"`; do
    flen=${#f}
    flen=$((flen - prefix_len))
    flen=$((flen - 6))
    echo "cp $f ${linux_target_build}/${f:$prefix_len:$flen}impnoin"
    cp $f ${linux_target_build}/${f:$prefix_len:$flen}impnoin
done
