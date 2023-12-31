#!/usr/bin/env python3

import os
import sys
import itertools
import subprocess
import tempfile
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.descriptions import (
    describe_symbol_type, describe_symbol_bind, describe_symbol_visibility,
    describe_symbol_shndx, describe_reloc_type, describe_dyn_tag,
    describe_symbol_other
    )


def get_noentry(linux_build_dir):
    noentry = set()
    for root,_,mods in os.walk(linux_build_dir):
        for mod in mods:
            temp = False
            kopath = os.path.join(root, mod)
            if mod.endswith(".ko.zst"):
                temp = True
                kopath = tempfile.mkstemp(suffix=".ko", dir="/tmp/")[1]
                os.system(f"zstdcat {os.path.join(root, mod)} > {kopath}")
            if mod.endswith(".ko.xz"):
                temp = True
                kopath = tempfile.mkstemp(suffix=".ko", dir="/tmp/")[1]
                os.system(f"xzcat {os.path.join(root, mod)} > {kopath}")
            if kopath.endswith(".ko"):
                flag = False
                with open(kopath, 'rb') as fd:
                    elf = ELFFile(fd)
                    for sec in elf.iter_sections():
                        if not isinstance(sec, SymbolTableSection):
                            continue
                        for sym in sec.iter_symbols():
                            flag = flag or (sym.name == 'init_module')
                #output = subprocess.check_output(['nm', kopath])
                #syms = [l.strip().split()[-1] for l in output.decode('latin-1').strip().split('\n')]
                #if 'init_module' not in syms:
                if not flag:
                    noentry.add(os.path.join(root, mod))
            if temp:
                os.system(f"rm {kopath}")
    return noentry

def get_deps(linux_build_dir):
    mod_dep = dict()
    rev_dep = dict()
    dep_path = os.path.join(linux_build_dir, "modules.dep")
    with open(dep_path, 'r') as fd:
        data = fd.read()
        for line in data.strip().split('\n'):
            key, deps = line.split(':')
            #key = os.path.basename(key)
            #if key.endswith(".ko"):
            #    key = key[:-3]
            key = os.path.join(linux_build_dir, key)
            if deps.strip():
                mod_dep[key] = []
                for d in deps.strip().split():
                    #d = os.path.basename(d.strip())
                    #if d.endswith(".ko"):
                    #    d = d[:-3]
                    d = os.path.join(linux_build_dir, d)
                    mod_dep[key].append(d)
                    if d in rev_dep:
                        rev_dep[d].add(key)
                    else:
                        rev_dep[d] = set([key])
    return rev_dep

def get_sym(mod, symty):
    symlist = []
    kopath = mod
    temp = False
    if mod.endswith(".ko.zst"):
        temp = True
        kopath = tempfile.mkstemp(suffix=".ko", dir="/tmp/")[1]
        os.system(f"zstdcat {mod} > {kopath}")
    if mod.endswith(".ko.xz"):
        temp = True
        kopath = tempfile.mkstemp(suffix=".ko", dir="/tmp/")[1]
        os.system(f"xzcat {mod} > {kopath}")
    output = subprocess.check_output(['nm', kopath])
    for line in output.decode('latin-1').strip().split('\n'):
        tup = line.strip().split()
        if len(tup) == 3:
            tup = tup[1:]
        ty, sym = tup
        if ty in symty:
            symlist.append(sym)
    if temp:
        os.system(f"rm {kopath}")
    return symlist

def get_data_deps(linux_build_path):
    data_deps = dict()
    rev_dep = get_deps(linux_build_path)
    for k in rev_dep:
        if len(rev_dep[k]) < 2:
            continue
        export_sym = set(get_sym(k, ['B', 'b', 'C', 'c', 'D', 'd', 'G', 'g', 'S', 's', 'T', 't', 'W', 'w', 'V', 'v']))
        import_symmap = dict()
        for mod in rev_dep[k]:
            isym = export_sym.intersection(set(get_sym(mod, ['U', 'u'])))
            if isym:
                import_symmap[mod] =isym

        #print(k, rev_dep[k])
        for m,n in itertools.combinations(import_symmap.keys(), 2):
            #m,n = sorted([m,n])
            if n in rev_dep and m in rev_dep[n]:
                continue
            if m in rev_dep and n in rev_dep[m]:
                continue
            shared_sym = import_symmap[m].intersection(import_symmap[n])
            if shared_sym:
                if m in data_deps:
                    if n in data_deps[m]:
                        data_deps[m][n].append((k, shared_sym))
                    else:
                        data_deps[m][n] = [(k, shared_sym)]
                else:
                    data_deps[m] = dict()
                    data_deps[m][n] = [(k, shared_sym)]
                if n in data_deps:
                    if m in data_deps[n]:
                        data_deps[n][m].append((k, shared_sym))
                    else:
                        data_deps[n][m] = [(k, shared_sym)]
                else:
                    data_deps[n] = dict()
                    data_deps[n][m] = [(k, shared_sym)]
                #print("  > ", m, ",", n, import_symmap[m].intersection(import_symmap[n]))
    return data_deps

if __name__ == "__main__":
    sys.exit(0)
