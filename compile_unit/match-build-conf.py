#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import glob
import re
from collections import defaultdict
from z3 import *

def get_bit(value, n):
    return ((value >> n & 1) != 0)

def main():
    if len(sys.argv) != 3:
        print("Usage:", sys.argv[0], "<obj-kconf db> <target objs>")
        return

    obj_confs = defaultdict(str)
    with open(sys.argv[1]) as file:
        for line in file:
            sp = line.rstrip().split()
            if len(sp) <= 1:
                continue
            conf = " ".join(sp[1:])
            z3syntax = re.sub("(CONFIG_[A-Za-z0-9_]+)", r"Bool('\1')", conf)
            obj_confs[sp[0]] = z3syntax

    with open(sys.argv[2]) as file:
        for line in file:
            cur = line.rstrip()
            if cur not in obj_confs:
                continue

            # find all satisfying assignments
            assigns = []
            curvars = list(set(re.findall(r"(Bool\('[^\']+'\))", obj_confs[cur])))
            combi = 2**len(curvars) - 1
            while combi >= 0:
                s = Solver()
                s.add(eval(obj_confs[cur]))
                assign = []
                i = 0
                while i < len(curvars):
                    assign.append("{0} == {1}".format(curvars[i], get_bit(combi, i)))
                    s.add(eval(curvars[i]) == get_bit(combi, i))
                    i = i + 1
                if s.check() == z3.sat:
                    assigns.append(assign)
                combi = combi - 1

            for obj in obj_confs:
                if cur == obj:
                    continue

                if obj_confs[cur] == obj_confs[obj]:
                    print(cur, obj)
                    continue

                for assign in assigns:
                    s = Solver()
                    s.add(eval(obj_confs[obj]))
                    objvars = set(re.findall(r"(Bool\('[^\']+'\))", obj_confs[obj]))
                    vacants = objvars - set(curvars)
                    for v in vacants:
                        # assume that unknown variables are False
                        s.add(eval(v) == False)
                    for a in assign:
                        s.add(eval(a))

                    if s.check() == z3.sat:
                        # print(s.model())
                        print(cur, obj)

if __name__ == '__main__':
    main()
