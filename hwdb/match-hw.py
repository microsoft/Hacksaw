#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import subprocess
import threading
import glob
import re
from collections import defaultdict

subtypes = set(["acpi*", "ahci", "amba", "auxiliary", "bcma", "cpu", "cxl", "dax", "dfl", "dmi", "dmi*", "eisa", "fsl-mc", "greybus", "hdaudio", "hid", "hsi", "i2c", "i3c", "ieee1394", "input", "ipack", "isa", "ishtp", "mcb", "mdio", "mei", "mhi", "mmc", "nd", "of", "pci", "pcmcia", "platform", "pnp", "rapidio", "rpmsg", "sata", "scsi", "sdio", "sdw", "serio", "slim", "spi", "spmi", "ssam", "ssb", "tbsvc", "tee", "typec", "ulpi", "usb", "usbfunc", "vfio_pci", "vfio-reset", "virtio", "vmbus", "wmi", "xen", "xen-backend"])

alias_mod = defaultdict(set)

def main():
    if len(sys.argv) != 3:
        print("Usage:", sys.argv[0], "<modules.alias> <hwinfo>")
        return

    with open(sys.argv[1]) as file:
        for line in file:
            if line[0] == '#':
                continue
            else:
                sp = line.rstrip().split()
                if len(sp) >= 3:
                    alias = " ".join(line.rstrip().split()[1:-1])
                    # ignore all matched IDs
                    if alias[:20] == "pci:v*d*sv*sd*bc*sc*" or alias[:33] == "input:b*v*p*e*-e*k*r*a*m*l*s*f*w*":
                        continue
                    mod = line.rstrip().split()[-1]
                    sp2 = alias.split(':')
                    if len(sp2) < 2 or sp2[0] not in subtypes:
                        continue
                    alias_mod[alias.replace('*', '.*').replace('?', '.')].add(mod)

    with open(sys.argv[2]) as file:
        for line in file:
            hwinfo = line.rstrip()
            matched = False
            for alias in alias_mod:
                for a in alias_mod[alias]:
                    if re.match(alias, hwinfo):
                        print(os.path.basename(a), hwinfo)
                        matched = True
            if matched == False:
                print('NONE', hwinfo)


if __name__ == '__main__':
    main()
