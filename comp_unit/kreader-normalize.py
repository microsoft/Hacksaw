#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import regex

def main() -> int:
    try:
        buf_list = []
        buf = ''
        is_first = True
        for l in sys.stdin:
            line = l.rstrip()
            if line[0] != ' ':
                if is_first == True:
                    buf = line
                    is_first = False
                else:
                    buf_list.append(buf)
                    buf = line
            else:
                buf = buf + ' ' + line.strip()

        for buf in buf_list:
            sp = buf.split()
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

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
