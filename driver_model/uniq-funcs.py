#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
from collections import defaultdict

def main() -> int:
    try:
        func_objs = defaultdict(list)
        for l in sys.stdin:
            obj, func = l.rstrip().split()
            func_objs[func].append(obj)

        for func in func_objs.keys():
            done = False
            for obj in func_objs[func]:
                if obj[-5:] == '.bc':
                    print(obj, func)
                    done = True
                    break
            if done == False:
                print(func_objs[func][0], func)

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
