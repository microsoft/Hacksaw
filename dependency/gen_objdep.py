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

def load_busreg_apis(busreg_list):
    busreg_apis = set()
    for ln in busreg_list:
        with open(ln, 'r') as fd:
            data = fd.read().strip()
            for line in data.split('\n'):
                line = line.strip()
                if not line:
                    continue
                _, api = line.split()
                busreg_apis.add(api)
    return busreg_apis

class ObjDeps(object):
    def __init__(self, linux_src, linux_build, btobj_deps):
        self.log = False

        self.obj_build_revdeps = btobj_deps

        self.import_table = collections.defaultdict(set)
        self.export_table = collections.defaultdict(set)
        self.off_map = collections.defaultdict(dict)
        self.fdep_map = collections.defaultdict(dict)
        self.frevdep_map = collections.defaultdict(set)
        self.mod_map = {}
        self.full_mod_map = {}
        self.drv_map = collections.defaultdict(set)
        self.gdat_cbs = collections.defaultdict(set)
        self.gdat_lnks = collections.defaultdict(dict)

        symoffpat = re.compile(r".*<(.*)> \(File Offset: (.*)\):$")
        for root,_,fs in os.walk(linux_build):
            for f in fs:
                f = os.path.join(root, f)
                mod = f[:-7]
                if f.endswith(".o.symtab"):
                    with open(f, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            line = line.strip()
                            if not line:
                                continue
                            ty, sym = line.split()[-2:]
                            if ty == 'U':
                                self.import_table[mod].add(sym)
                            else:
                                addr = line.split()[0]
                                self.export_table[mod].add(sym)
                                if sym not in self.mod_map:
                                    self.mod_map[sym] = mod
                                    self.full_mod_map[sym] = set([mod])
                                else:
                                    self.full_mod_map[sym].add(mod)
                                    tmp = self.mod_map[sym]
                                    if len(os.path.dirname(mod)) > len(os.path.dirname(self.mod_map[sym])):
                                        tmp = mod
                                    self.mod_map[sym] = tmp
                elif f.endswith(".o.symoff"):
                    with open(f, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            m = re.match(symoffpat, line)
                            sym, off = m.group(1, 2)
                            self.off_map[mod][sym] = int(off, 16)
                elif f.endswith(".o.imptab"):
                    with open(f, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            sym, call = line.strip().split(' : ')
                            if sym not in self.fdep_map[mod]:
                                self.fdep_map[mod][sym] = set()
                            self.fdep_map[mod][sym].add(call)
                            self.frevdep_map[call].add((sym, mod))
                elif f.endswith(".o.symlnk"):
                    with open(f, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            func, gdat = line.strip().split(' : ')
                            if func not in self.gdat_lnks[mod]:
                                self.gdat_lnks[mod][func] = set()
                            self.gdat_lnks[mod][func].add(gdat)
                elif f.endswith(".o.symcbs"):
                    with open(f, 'r') as fd:
                        data = fd.read()
                        for line in data.strip().split('\n'):
                            if not line:
                                continue
                            gdat, cb = line.strip().split(' : ')
                            self.gdat_cbs[gdat].add(cb)
                elif f.endswith('.mod'):
                    ko = os.path.join(root, f[:-4]+".ko")
                    assert (os.path.exists(ko))
                    with open(os.path.join(root, f), 'r') as fd:
                        objfiles = [obj for obj in fd.read().strip().split('\n')]
                        for objfile in objfiles:
                            # get makefile
                            if objfile.startswith("include/"):
                                continue
                            mk = os.path.join(linux_src, os.path.dirname(objfile), "Makefile")
                            while not os.path.exists(mk):
                                mk = os.path.join(os.path.dirname(mk), "Kbuild")
                                if os.path.exists(mk):
                                    break
                                pdir = os.path.dirname(os.path.dirname(mk))
                                mk = os.path.join(pdir, "Makefile")
                            # Possible third-party driver
                            if os.path.dirname(mk) == os.path.normpath(linux_src):
                                continue
                            assert (os.path.exists(mk))
        
                            self.drv_map[os.path.join(linux_build, objfile)].add(ko)
        
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

    def funcdeps(self, reg_apis):
        # Build Function dependency
        function_uses = collections.defaultdict(set)
        for mod in self.fdep_map:
            if "vmlinux" in os.path.basename(mod):
                continue
            #print(mod, len(fdep_map[mod]))
            for func in self.fdep_map[mod]:
                for sym in self.fdep_map[mod][func]:
                    # Skip Local symbol
                    if sym in self.fdep_map[mod]:
                        continue
                    # Locate symbol in export table
                    if sym in self.full_mod_map:
                        for dmod in self.full_mod_map[sym]:
                            if "vmlinux" in os.path.basename(dmod):
                                continue
                            if sym in self.export_table[dmod]:
                                function_uses[(sym, dmod)].add((mod, func))
        
        if self.log:
            with open("function_deps.list", 'w') as fd:
                for sym, dmod in function_uses:
                    if sym not in reg_apis:
                        continue
                    if dmod in self.drv_map:
                        fd.write(f"{sym}, {str(self.drv_map[dmod])}\n")
                    else:
                        fd.write(f"{sym}, {dmod}:\n")
                    for mod, func in function_uses[(sym, dmod)]:
                        if mod in self.drv_map:
                            #print(self.drv_map[mod])
                            assert (len(self.drv_map[mod]) == 1)
                            mod = list(self.drv_map[mod])[0]
                        else:
                            # Built-in
                            pass
                        fd.write(f"    {func}, {mod}\n")

        ret = collections.defaultdict(set)
        for sym, dmod in function_uses:
            if sym not in reg_apis:
                continue
            if dmod in self.drv_map:
                dmodset = self.drv_map[dmod]
            else:
                dmodset = set([dmod])
            for o in dmodset:
                for mod, func in function_uses[(sym, dmod)]:
                    if mod in self.drv_map:
                        #print(self.drv_map[mod])
                        assert (len(self.drv_map[mod]) == 1)
                        mod = list(self.drv_map[mod])[0]
                    else:
                        # Built-in
                        pass
                    ret[(sym, o)].add((func, mod))
        return ret

    def _load_sysmap(self, sysmap):
        syms = set()
        with open(sysmap, 'r') as fd:
            data = fd.read().strip()
            for line in data.split('\n'):
                line = line.strip()
                sym = line.split()[-1]
                syms.add(sym)
        return syms

    def objdeps(self, sysmap):
        if self.log:
            with open("dupsym.list", 'w') as fd:
                for sym in self.full_mod_map:
                    if len(self.full_mod_map[sym]) > 2:
                        print(sym, self.full_mod_map[sym])
                        fd.write(f"{sym}, {self.full_mod_map[sym]}\n")
        
        # Build .o dependency
        sym_deps = collections.defaultdict(set)
        obj_deps = collections.defaultdict(set)
        print(len(self.import_table))
        print(len(self.export_table))
        for depmod in self.export_table:
            for mod in self.import_table:
                if depmod == mod:
                    continue
                for sym in self.import_table[mod].intersection(self.export_table[depmod]):
                    sym_deps[sym].add(mod)
                    depmod = self.mod_map[sym]
                    obj_deps[depmod].add(mod)
        
        #load database system.map
        initcalls = set()
        for sym in self._load_sysmap(sysmap):
            if sym.startswith("__initcall__kmod_"):
                initcalls.add(hwfilter.initcall_sym2init(sym))
        
        indi_mod = set()
        seen = set()
        with open('linkdeps.list', 'w') as fd:
            for sym in initcalls:
                mod = self.mod_map[sym]
                #print(sym, mod, obj_deps[(sym, mod)])
                for relsym in self.export_table[mod]:
                    if mod in obj_deps:
                        #print(sym, mod, relsym, len(obj_deps[mod]))
                        fd.write(f"{relsym}, {mod}, {len(obj_deps[mod])}\n")
                        seen.add(sym)
                    else:
                        indi_mod.add(mod)
        
        with open('nodep.list', 'w') as fd:
            for sym in initcalls:
                if not self.export_table[self.mod_map[sym]].intersection(seen):
                    fd.write(f"{sym}, {self.mod_map[sym]}\n")

    def related(self, sym):
        if sym not in self.mod_map:
            return None
        m = self.mod_map[sym]
        testmods = set()
        if m in self.obj_build_revdeps:
            testmods = self.obj_build_revdeps[m]
            testmods.add(m)
        else:
            testmods.add(m)

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

if __name__ == "__main__":
    sys.exit(0)
