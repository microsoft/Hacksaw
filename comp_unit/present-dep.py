#!/usr/bin/env python3
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
from collections import defaultdict
from argparse import ArgumentParser, Namespace

def main():
    if len(sys.argv) != 2:
        print("Usage: " + sys.argv[0] + " <file>")
        return

    obj_cu = defaultdict(list)

    with open(sys.argv[1]) as file:
        for line in file:
            sp = line.rstrip().split()
            obj_cu[sp[0]].append(sp[1])

    for obj in sorted(obj_cu):
        print(obj, end=":")
        for cu in obj_cu[obj]:
            print(" " + cu, end="")
        print("")

if __name__ == '__main__':
    sys.exit(main(parse_arguments()))
