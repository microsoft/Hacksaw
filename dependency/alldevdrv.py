#!/usr/bin/env python3

import os
import sys
import checkmodsym

LINUX_BUILD="/home/hu/linux/build_llvm"

alldrvlist = sys.argv[1]
bucket = dict()
total_devdrv = set()
with open(alldrvlist, 'r') as fd:
    data = fd.read().strip().split('\n')
    for line in data:
        ty,fn = line.strip().split(':')
        if '.built-in.a' in fn:
            continue
        if fn.endswith(".mod.bcmerged"):
            fn = fn[:-12]+"ko"
        total_devdrv.add(fn)
        if ty in bucket:
            bucket[ty].add(fn)
        else:
            bucket[ty] = set([fn])

l = []
for k in bucket:
    l.append((k, len(bucket[k])))
l.sort(key=lambda x: x[1])
for t in l:
    print(t)
print("Total: ", len(total_devdrv))


# Build Module dependencies
mod_dep = dict()
rev_dep = dict()
dep_path = os.path.join(LINUX_BUILD, "modules.dep")
with open(dep_path, 'r') as fd:
    data = fd.read()
    for line in data.strip().split('\n'):
        key, deps = line.split(':')
        #key = os.path.basename(key)
        #if key.endswith(".ko"):
        #    key = key[:-3]
        key = os.path.join(LINUX_BUILD, key)
        if deps.strip():
            mod_dep[key] = []
            for d in deps.strip().split():
                #d = os.path.basename(d.strip())
                #if d.endswith(".ko"):
                #    d = d[:-3]
                d = os.path.join(LINUX_BUILD, d)
                mod_dep[key].append(d)
                if d in rev_dep:
                    rev_dep[d].add(key)
                else:
                    rev_dep[d] = set([key])

devdrv_symdeps = dict()
for k in bucket:
    devdrv_symdeps[k] = set()
    for mod in bucket[k]:
        if mod in rev_dep:
            devdrv_symdeps[k].update(rev_dep[mod])
    #assert (not devdrv_symdeps[mod].intersection(bucket.keys()))
print("Sym Deps:")
for k in devdrv_symdeps:
    if devdrv_symdeps[k]:
        print(k, len(devdrv_symdeps[k].difference(total_devdrv)), "/", len(devdrv_symdeps[k]))
        #print(devdrv_symdeps[k].difference(total_devdrv))
#exit(0)

# Data Dependencies
data_deps = checkmodsym.get_data_deps(LINUX_BUILD)
devdrv_datdeps = dict()
for k in bucket:
    devdrv_datdeps[k] = set()
    for mod in bucket[k]:
        if mod in data_deps:
            devdrv_datdeps[k].update(data_deps[mod].keys())
    for mod in devdrv_symdeps[k]:
        if mod in data_deps:
            devdrv_datdeps[k].update(data_deps[mod].keys())

print("Data Deps:")
for k in devdrv_datdeps:
    if devdrv_datdeps[k]:
        print(k, len(devdrv_datdeps[k].difference(total_devdrv).difference(devdrv_symdeps[k])), "/", len(devdrv_datdeps[k]))
        print(devdrv_datdeps[k].difference(total_devdrv).difference(devdrv_symdeps[k]))
exit(0)

with open("/home/hu/existing_mod.list", 'r') as fd:
    data = fd.read().strip().split('\n')
    for line in data:
        mod = line.strip().split('/')[-1]
        if mod.endswith(".ko"):
            mod = mod[:-3]
            m = mod+".mod.bcmerged"
            for f in bucket['struct.acpi_device_id']:
                if m == f.split('/')[-1]:
                    print(f, ":", rev_dep[mod] if mod in rev_dep else [])
