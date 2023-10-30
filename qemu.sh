#!/bin/bash

#qemu-system-x86_64 --enable-kvm -cpu host -smp cores=2,threads=1,sockets=1 -m 2048 \
#    -display none -serial stdio \
#    -kernel ./out/repack/vmlinux.unpack.patched \
#    -append "console=ttyS0 earlyprintk" \
#    -initrd ./out/repack/ramfs/newrd.img \
#    -hda $1 \
#    -hdb ./phoronix.raw
qemu-system-x86_64 --enable-kvm -cpu host -smp cores=2,threads=1,sockets=1 -m 2048 \
    -display none -serial stdio \
    -hda $1 \
    -hdb ./phoronix.raw
