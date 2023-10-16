#!/bin/bash

mv modinit.log modinit.log.old

KERN_SRC="$1"
cwd=$(dirname $(realpath $0))

pushd ${KERN_SRC}

while read line; do
    grep -wrF "${line}" .| grep -E ":${line}[\s\(]*"|grep -v "#" >> $cwd/modinit.log;
done < $cwd/modinitcb_macro.list

popd
