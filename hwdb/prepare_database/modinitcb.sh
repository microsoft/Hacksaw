#!/bin/bash

KERN_SRC="$1"
OUTPUT_PATH="$2"
cwd=$(dirname $(realpath $0))

pushd ${KERN_SRC}

while read line; do
    grep -wrF "${line}" .| grep -E ":${line}[\s\(]*"|grep -v "#" >> $OUTPUT_PATH/modinit.log;
done < $cwd/modinitcb_macro.list

popd
