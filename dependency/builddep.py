#!/usr/bin/env python3

import os
import sys
import glob
import subprocess

CURDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURDIR, "..", "kernel_patch"))
import hwfilter
import checkmodsym

def norm_mod(mod):
    m = mod
    if m.endswith(".ko.zst"):
        m = m[:-4]
    if m.endswith(".ko.xz"):
        m = m[:-3]
    return m

def get_deps(mod_dir):
    mod_dep = dict()
    rev_dep = dict()
    dep_path = os.path.join(mod_dir, "modules.dep")
    if not os.path.exists(dep_path):
        for r,_,fs in os.walk(mod_dir):
            if 'modules.dep' in fs:
                dep_path = os.path.join(r, 'modules.dep')
                break
    with open(dep_path, 'r') as fd:
        data = fd.read()
        for line in data.strip().split('\n'):
            key, deps = line.split(':')
            key = norm_mod(os.path.basename(key))
            if key.endswith(".ko"):
                key = key[:-3]
            if deps.strip():
                mod_dep[key] = set()
                for d in deps.strip().split():
                    d = norm_mod(os.path.basename(d.strip()))
                    if d.endswith(".ko"):
                        d = d[:-3]
                    mod_dep[key].add(d)
                    if d in rev_dep:
                        rev_dep[d].add(key)
                    else:
                        rev_dep[d] = set([key])
    return mod_dep, rev_dep

def get_core_deps(check_dir, driver_map, busreg_apis):
    checkdrv = dict()
    for root,_,mods in os.walk(check_dir):
        for mod in mods:
            mname = norm_mod(mod)
            if mname.endswith('.ko'):
                m = os.path.basename(mname)[:-3]
                if m not in checkdrv:
                    checkdrv[m] = set()
                checkdrv[m].add(os.path.join(root, mod))

    regprov = dict()
    for mod in checkdrv:
        if mod not in driver_map:
            for p in checkdrv[mod]:
                for sym in checkmodsym.get_sym(p, ['t', 'T']):
                    if sym in busreg_apis:
                        if mod not in regprov:
                            regprov[mod] = set()
                        regprov[mod].add(sym)
    #print(len(regprov))

    #dep_map,_ = get_deps(os.path.join(check_dir, "lib/modules", mod_ver))
    dep_map,_ = get_deps(check_dir)
    coredepmap = dict()
    for mod in checkdrv:
        for p in checkdrv[mod]:
            for sym in checkmodsym.get_sym(p, ['u', 'U']):
                for d in regprov:
                    if sym in regprov[d]:
                        if d not in coredepmap:
                            coredepmap[d] = set()
                        if mod in driver_map:
                            coredepmap[d].add(mod)
                        else:
                            # One more level of Driver Dependents
                            for dm in dep_map[mod]:
                                if dm in driver_map:
                                    coredepmap[d].add(dm)
    #print(len(coredepmap))
    return coredepmap

if __name__ == "__main__":
    target_img = sys.argv[1]
    check_dir = sys.argv[2]

    hwconf = "../hwenv/hyperv.txt"
    devdb_path = "../gen_database/platform.db"

    _,_,driver_map,_ = hwfilter.load_db(hwconf, devdb_path)
    os.system(f"guestmount -a {target_img} --rw -i {check_dir}")

    modlist,_ = hwfilter.get_target_info(check_dir)

    mod_ver = hwfilter.get_kernel_ver(check_dir)
    mod_dir = os.path.join(check_dir, "lib/modules/", mod_ver)
    coredepmap = get_core_deps(mod_dir, driver_map)

    with open('dep.log', 'w') as fd:
        for d in coredepmap:
            fd.write(d+' : '+ str([m for m in coredepmap[d]]) + '\n')
    os.system(f"umount {check_dir}")
