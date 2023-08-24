#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import regex
import multiprocess as mp
from argparse import ArgumentParser, Namespace
from typing import Dict, List

def main() -> int:
    try:
        unit_start = False
        unit_str = ''
        for l in sys.stdin:
            line = l.rstrip()
            stripped = l.strip()
            if line == stripped:
                if unit_start == False:
                    unit_str = stripped
                    unit_start = True
                else:
                    sp = unit_str.split()
                    unit = sp[0]
                    z3 = ' '.join(sp[1:])
                    if unit[-2:] == '.o' and z3 != 'True':
                        unit = os.path.normpath(unit)
                        z3 = regex.sub('\$\(ARCH\)=arm', 'CONFIG_ARM', z3)
                        z3 = regex.sub('\$\(ARCH\)=arm64', 'CONFIG_ARM64', z3)
                        z3 = regex.sub('BITS=32', 'CONFIG_32BIT', z3)
                        z3 = regex.sub('BITS=64', 'CONFIG_64BIT', z3)
                        z3 = regex.sub(' 0,', ' False,', z3)
                        z3 = regex.sub(' 1,', ' True,', z3)

                        print(unit, z3)
                    unit_str = ''
                    unit_start = False
            else:
                unit_str = unit_str + ' ' + stripped


    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
