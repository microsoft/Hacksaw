#!/bin/bash
curdir=$(dirname $(realpath $0))
linux_build=$(realpath "$1")

for f in `find ${linux_build} -name "*.o"`; do
    nm $f | grep -e " [t|T|w|W|U] " > ${f}.symtab
done
