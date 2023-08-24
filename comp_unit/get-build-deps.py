#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import re
import multiprocessing as mp
import math
from collections import defaultdict
from z3 import *
from argparse import ArgumentParser, Namespace
from typing import Dict, List

obj_kcvars = defaultdict(set)
obj_z3 = defaultdict(str)
objs = []
objs_sat = []

obj_kconf_expr_file = ""
dotconfigs = set([])
nworkers = 1

def parse_arguments(cli_args: List[str] = None) -> Namespace:
    parser = ArgumentParser(description='Get build dependencies between object files')
    parser.add_argument('-f', '--obj-kconf-expr-file', action='store', required=True,
                        help='object-kconfig-expression file path')
    parser.add_argument('-c', '--dotconfig-file', action='store', required=True,
                        help='kernel dotconfig file path')
    parser.add_argument('-n', '--num-workers', action='store',
                        help='the number of worker threads')
    return parser.parse_args(args=cli_args)

def load_configs(args: Namespace) -> Dict:
    try:
        if not os.path.exists(args.obj_kconf_expr_file):
            print(args.obj_kconf_expr_file, "does not exist", file=sys.stderr)
            return False

        if not os.path.exists(args.dotconfig_file):
            print(args.dotconfig_file, "does not exist", file=sys.stderr)
            return False

        global obj_kconf_expr_file 
        obj_kconf_expr_file=os.path.realpath(args.obj_kconf_expr_file)

        global nworkers
        if args.num_workers != None:
            nworkers = int(args.num_workers)

        global dotconfigs
        with open(args.dotconfig_file) as file:
            for line in file:
                l = line.rstrip()
                if len(l) == 0 or l[0] == '#':
                    continue
                else:
                    sp = l.split('=')
                    if len(sp) == 2 and (sp[1] == 'y' or sp[1] == 'm'):
                        dotconfigs.add("Bool('" + sp[0] + "')")

    except Exception as err:
        print(err)
        if err == "Really Bad":
            raise err

    return True

def get_bit(value, n):
    return ((value >> n & 1) != 0)

def execute_check_sat(obj_id):
    result = -1
    cvars = set(re.findall(r"(Bool\('[^\']+'\))", obj_z3[objs[obj_id]]))

    s = Solver()
    s.add(eval(obj_z3[objs[obj_id]]))
    for cv in cvars:
        if cv in dotconfigs:
            s.add(eval(cv) == True)
        else:
            s.add(eval(cv) == False)

    if s.check() == z3.sat:
        result = obj_id
    else:
        result = -1

    return result

def check_build_deps(parent_id, candidate_ids):
    pvars = set(re.findall(r"(Bool\('[^\']+'\))", obj_z3[objs_sat[parent_id]]))

    results = []
    for candidate_id in candidate_ids:
        if obj_z3[objs_sat[parent_id]] == obj_z3[objs_sat[candidate_id]]:
            results.append(candidate_id)
            continue

        s = Solver()
        s.add(eval(obj_z3[objs_sat[candidate_id]]))
        for pv in pvars:
            if pv in dotconfigs:
                s.add(eval(pv) == True)
            else:
                s.add(eval(pv) == False)

        if s.check() == z3.sat:
            results.append(candidate_id)

    return results

def execute_check_build_deps_base(parent_id, candidate_ids):
    results = []
    children_ids = check_build_deps(parent_id, candidate_ids)
    for ci in children_ids:
        results.append([objs_sat[parent_id], objs_sat[ci]])
    return results

def execute_check_build_deps_left(parent_id):
    candidate_ids = []
    for candidate_id in range(parent_id+1, math.floor(len(objs_sat)/2)):
        if len(obj_kcvars[objs_sat[candidate_id]].difference(obj_kcvars[objs_sat[parent_id]])) == 0:
            candidate_ids.append(candidate_id)

    if len(candidate_ids) == 0:
        return []

    return execute_check_build_deps_base(parent_id, candidate_ids)

def execute_check_build_deps_right(parent_id):
    candidate_ids = []
    for candidate_id in range(max([parent_id+1, math.floor(len(objs_sat)/2)]), len(objs_sat)):
        if len(obj_kcvars[objs_sat[candidate_id]].difference(obj_kcvars[objs_sat[parent_id]])) == 0:
            candidate_ids.append(candidate_id)

    if len(candidate_ids) == 0:
        return [] 

    return execute_check_build_deps_base(parent_id, candidate_ids)

def main(args: Namespace = parse_arguments()) -> int:
    try:
        if not load_configs(args):
            return 1

        with open(obj_kconf_expr_file) as file:
            for line in file:
                sp = line.rstrip().split()
                if len(sp) <= 1:
                    continue
                obj = sp[0].replace('$(BITS)', '64') # FIXME
                if obj.find('$') != -1:
                    continue
                conf = " ".join(sp[1:])
                obj_z3[obj] = re.sub("(CONFIG_[A-Za-z0-9_]+)", r"Bool('\1')", conf)
                obj_kcvars[obj] = set(re.findall(r"(CONFIG_[A-Za-z0-9_]+)", conf))

        global objs
        objs = obj_kcvars.keys()
        objs = sorted(objs)
        indices = range(len(objs))
        pool = mp.Pool(nworkers)
        results = pool.map(execute_check_sat, indices)
        pool.close()
        pool.join()

        global objs_sat
        set_sat = set(results)
        set_sat.remove(-1)
        for idx in set_sat:
            objs_sat.append(objs[idx])
        objs_sat = sorted(objs_sat)

        del objs

        indices = range(len(objs_sat))
        pool = mp.Pool(nworkers)
        results = pool.map(execute_check_build_deps_left, indices)
        pool.close()
        pool.join()

        pool = mp.Pool(nworkers)
        results_right = pool.map(execute_check_build_deps_right, indices)
        pool.close()
        pool.join()

        results = results + results_right

        for res in results:
            if len(res) != 0:
                for res2 in res:
                    print(res2[0], res2[1])

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main(parse_arguments()))
