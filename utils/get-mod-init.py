#!/usr/bin/env python3
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

import os.path
import sys
import subprocess
import re

def main():
    if len(sys.argv) != 2:
        print("Usage: " + sys.argv[0] + " <module>")
        return

    result = subprocess.run(['objdump', '-t', sys.argv[1]], stdout=subprocess.PIPE)
    symtbl = result.stdout.decode('utf-8').split('\n')
    funcs = []
    for sym in symtbl:
        if re.search(r"F\s(|.init).text(|.early)", sym):
            funcs.append(sym)

    initmod = ""
    for func in funcs:
        if re.search(r"\sinit_module$", func):
            initmod = func
            break

    if initmod == "":
        print(os.path.basename(sys.argv[1])[-3] + "\tNOINIT")
        return

    spl = initmod.split()
    size = spl[0]
    sect = spl[3]
    addr = spl[4]

    initfn = "NOINIT"
    for func in funcs:
        spl = func.split()
        if spl[5] != "init_module" and spl[0] == size and spl[3] == sect and spl[4] == addr:
            initfn = spl[5]
            break

    print(os.path.basename(sys.argv[1])[-3] + "\t" + initfn)

if __name__ == '__main__':
    main()
