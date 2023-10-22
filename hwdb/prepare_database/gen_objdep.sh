#!/bin/bash

KERN_SRC=$(realpath "$1")
curdir=$(dirname $(realpath $0))
linux_build="${KERN_SRC}/build_llvm"

for f in `find ${linux_build} -name "*.o"`; do
       	nm $f | grep -e " [t|T|U] " > ${f}.symtab
	objdump -Fd $f |grep "File Offset"|grep "):$" > ${f}.symoff
done
