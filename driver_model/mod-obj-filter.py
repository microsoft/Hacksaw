#!/usr/bin/env python3
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
from collections import defaultdict

def main() -> int:
    try: 
        dup_funcs = defaultdict(set)
        for l in sys.stdin:
            line = l.rstrip()
            sp = line.split()
            dup_funcs[sp[-1]].add(line)

        for func in dup_funcs.keys():
            if len(dup_funcs[func]) != 1:
                for elem in dup_funcs[func]:
                    if elem.find(".ko.hacksaw.bc") != -1:
                        print(elem)
                        break
            else:
                for elem in dup_funcs[func]:
                    print(elem)

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
