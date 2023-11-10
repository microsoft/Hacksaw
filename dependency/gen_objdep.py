#!/usr/bin/env python3

import os
import re
import sys
import collections

CURDIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(CURDIR, "..", "kernel_patch"))
import hwfilter
sys.path.append(os.path.join(CURDIR, "..", "hwdb", "prepare_database"))
import modinitcb

module_symbols = set([
    'module_get',
    'modver_version_show',
    'cleanup_module',
    'do_init_module',
    'init_module',
    'load_module',
    'module_put',
    'module_put_and_exit',
    'print_modules',
    'retpoline_module_ok',
    'try_module_get'
])

def is_module_symbol(sym):
    sym_norm = re.sub("^_*", "", sym)
    if sym_norm in module_symbols or sym_norm[:5] == "llvm.":
        return True
    return False

# symbols that shouldn't be removed
permanent_symbols = set([
    "thermal_init",
    "mdiobus_get_phy",
    "should_remove_suid"
])
def load_asm_symbols(asm_sym_list):
    with open(asm_sym_list, 'r') as f:
        for line in f:
            sym_norm = re.sub("^_*", "", line.rstrip())
            permanent_symbols.add(sym_norm)

def is_permanent_symbol(sym):
    sym_norm = re.sub("^_*", "", sym)
    if sym_norm in permanent_symbols:
        return True
    return False

def load_btobj_deps(linux_build, builtin_objdeplist):
    obj_build_revdeps = collections.defaultdict(set)
    with open(builtin_objdeplist, 'r') as fd:
        data = fd.read().strip()
        for line in data.split('\n'):
            if not line:
                continue
            linked, *objs = line.strip().split()
            assert (linked[-1] == ':')
            linked = linked[:-1]
            linked = os.path.join(linux_build, linked)
            for o in objs:
                o = os.path.join(linux_build, o)
                obj_build_revdeps[o].add(linked)
    return obj_build_revdeps

def load_busreg_apis(linux_build, busreg_list):
    busreg_apis = set()
    for ln in busreg_list:
        with open(ln, 'r') as fd:
            data = fd.read().strip()
            for line in data.split('\n'):
                line = line.strip()
                if not line:
                    continue
                obj, api = line.split()
                if not obj.endswith(".o.bc"):
                    obj = obj[:-2] + "o.bc"
                obj = os.path.join(linux_build, obj[:-3])
                obj = re.sub('-', '_', obj)
                busreg_apis.add((obj, api))
    return busreg_apis

def normalize_object_name(fname, curext='.o', newext='.o', curpath=''):
    obj = fname[:-len(curext)]
    if curpath != '':
        obj = os.path.join(curpath, obj)
    obj = re.sub('-', '_', obj)
    return obj + newext

class ObjDeps(object):
    def __init__(self, linux_src, linux_build, btobj_deps):
        self.log = False

        self.obj_build_revdeps = btobj_deps

        self.import_table = collections.defaultdict(set)
        self.export_table = collections.defaultdict(set)
        self.global_export_table = collections.defaultdict(set)
        self.fdep_map = collections.defaultdict(dict)
        self.frevdep_map = collections.defaultdict(set)
        self.mod_map = collections.defaultdict(set)
        self.drv_map = collections.defaultdict(set)
        self.gdat_cbs = collections.defaultdict(set)
        self.gdat_lnks = collections.defaultdict(dict)
        self.fpref_map = collections.defaultdict(dict)
        self.fpref_revmap = collections.defaultdict(dict)

        for root,_,fs in os.walk(linux_build):
            for fname in fs:
                fpath = os.path.join(root, fname)
                if fname.endswith(".o.symtab") and not fname.endswith(".mod.o.symtab"):
                    mod = normalize_object_name(fname, ".o.symtab", ".o", root)
                    with open(fpath, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            line = line.strip()
                            if not line:
                                continue
                            ty, sym = line.split()[-2:]
                            if ty == 'U':
                                self.import_table[mod].add(sym)
                            else:
                                self.export_table[mod].add(sym)
                                if ty == 'T':
                                    self.global_export_table[mod].add(sym)
                                self.mod_map[sym].add(mod)
                elif fname.endswith(".o.imptab") and not fname.endswith(".mod.o.imptab"):
                    mod = normalize_object_name(fname, ".o.imptab", ".o", root)
                    with open(fpath, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            sym, call = line.strip().split(' : ')
                            if is_module_symbol(sym) or is_module_symbol(call):
                                continue
                            if sym not in self.fdep_map[mod]:
                                self.fdep_map[mod][sym] = set()
                            self.fdep_map[mod][sym].add(call)
                            self.frevdep_map[call].add((sym, mod))

                elif fname.endswith(".o.symlnk") and not fname.endswith(".mod.o.symlnk"):
                    mod = normalize_object_name(fname, ".o.symlnk", ".o", root)
                    with open(fpath, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            func, gdat = line.strip().split(' : ')
                            if is_module_symbol(func) or is_module_symbol(gdat):
                                continue
                            if func not in self.gdat_lnks[mod]:
                                self.gdat_lnks[mod][func] = set()
                            self.gdat_lnks[mod][func].add(gdat)
                elif fname.endswith(".o.symcbs") and not fname.endswith(".mod.o.symcbs"):
                    mod = normalize_object_name(fname, ".o.symcbs", ".o", root)
                    with open(fpath, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            gdat, cb = line.strip().split(' : ')
                            if is_module_symbol(gdat) or is_module_symbol(cb):
                                continue
                            self.gdat_cbs[gdat].add(cb)
                elif fname.endswith(".o.fptref") and not fname.endswith(".mod.o.fptref"):
                    mod = normalize_object_name(fname, ".o.fptref", ".o", root)
                    with open(fpath, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            sym, fpref = line.strip().split(' : ')
                            if is_module_symbol(sym) or is_module_symbol(fpref):
                                continue
                            if sym not in self.fpref_map[mod]:
                                self.fpref_map[mod][sym] = set()
                            if fpref not in self.fpref_revmap[mod]:
                                self.fpref_revmap[mod][fpref] = set()
                            self.fpref_map[mod][sym].add(fpref)
                            self.fpref_revmap[mod][fpref].add(sym)
                elif fname.endswith('.mod'):
                    ko = normalize_object_name(fname, ".mod", ".ko", root)
                    with open(fpath, 'r') as fd:
                        objfiles = [obj for obj in fd.read().strip().replace('\n', ' ').split(' ')]
                        for objfile in objfiles:
                            # get makefile
                            if objfile.startswith("include/"):
                                continue
                            mk = os.path.join(linux_src, os.path.dirname(objfile), "Makefile")
                            while not os.path.exists(mk):
                                mk = os.path.join(os.path.dirname(mk), "Kbuild")
                                if os.path.exists(mk) or mk == "/Kbuild":
                                    break
                                pdir = os.path.dirname(os.path.dirname(mk))
                                mk = os.path.join(pdir, "Makefile")
                            # Possible third-party driver
                            if os.path.dirname(mk) == os.path.normpath(linux_src):
                                continue
                            assert (os.path.exists(mk))
                            self.drv_map[normalize_object_name(objfile, curpath=linux_build)].add(ko)
        
        # link function through global variables
        for mod in self.gdat_lnks:
            for func in self.gdat_lnks[mod]:
                for gv in self.gdat_lnks[mod][func]:
                    if gv not in self.gdat_cbs:
                        continue
                    for cb in self.gdat_cbs[gv]:
                        if func not in self.fdep_map[mod]:
                            self.fdep_map[mod][func] = set()
                        self.fdep_map[mod][func].add(cb)
                        self.frevdep_map[cb].add((func, mod))

    def imports(self, mod, sym):
        if mod not in self.import_table:
            return None
        return self.import_table[mod]

    def related(self, mod, sym):
        if mod not in self.mod_map[sym]:
            return None
        testmods = set()
        if mod in self.obj_build_revdeps:
            testmods = self.obj_build_revdeps[mod]
            testmods.add(mod)
        else:
            testmods.add(mod)

        candid = collections.defaultdict(set)
        for mod in testmods:
            if mod not in self.export_table:
                continue
            for relsym in self.export_table[mod]:
                if mod in self.drv_map:
                    assert (len(self.drv_map[mod])==1)
                    mod = list(self.drv_map[mod])[0]
                for caller, cmod in self.frevdep_map[relsym]:
                    if cmod in self.drv_map:
                        cmod = list(self.drv_map[cmod])[0]
                    candid[(relsym, mod)].add((caller, cmod))
        return candid

    def has_referencer(self, mod, sym, patched_syms):
        if mod not in self.fpref_revmap or sym not in self.fpref_revmap[mod]:
            return False

        refers = self.fpref_revmap[mod][sym]
        patched_refers = set([])
        for m,s in patched_syms:
            if m == mod:
                patched_refers.add(s)

        if len(refers - patched_refers) == 0:
            return False
        return True

    def get_mods(self, sym, global_only=False):
        if sym not in self.mod_map:
            return None
        if global_only == False:
            return self.mod_map[sym]

        gmods = set([])
        for mod in self.mod_map[sym]:
            if mod in self.global_export_table and sym in self.global_export_table[mod]:
                gmods.add(mod)
        if len(gmods) == 0:
            return None
        return gmods

    def is_module(self, obj):
        if obj in self.drv_map:
            return True
        return False

if __name__ == "__main__":
    sys.exit(0)
