#!/usr/bin/env python3
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
from collections import defaultdict

def main() -> int:
    try:
        obj_cu = defaultdict(list)
        for l in sys.stdin:
            line = l.rstrip()
            sp = line.split()
            obj_cu[sp[0]].append(sp[1])

        for obj in sorted(obj_cu):
            print(obj, end=":")
            for cu in obj_cu[obj]:
                print(" " + cu, end="")
            print("")

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
