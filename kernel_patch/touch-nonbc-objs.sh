#!/bin/bash
CURDIR=$(dirname $(realpath $0))
BUILDDIR=$(realpath "$1")

for f in `find $BUILDDIR -name "*.o"`; do
    if [ ! -f "${f}.bc" ] && [ ! -f "${f::-1}mod.o.bc" ] ; then
        touch ${f}.nonbc
    fi
done
