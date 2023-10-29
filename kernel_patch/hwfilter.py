#!/usr/bin/env python3

import os
import stat
import re
import sys
import glob
import time
import shutil
import pickle
import tempfile
import subprocess
import checkmodsym
import disasm

CURDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURDIR, "..", "dependency"))
import builddep
import gen_objdep

def load_alldrv(linux_build):
    alldrv_list = set()
    for root,_,mods in os.walk(linux_build):
        for mod in mods:
            if mod.endswith(".ko"):
                mod = mod[:-3]
                alldrv_list.add(mod)
    return alldrv_list

def load_alldrv_path(linux_build):
    alldrv_list = dict()
    for root,_,mods in os.walk(linux_build):
        for mod in mods:
            if mod.endswith(".ko"):
                bmod = mod[:-3]
                if bmod not in alldrv_list:
                    alldrv_list[bmod] = set()
                alldrv_list[bmod].add(os.path.join(os.path.relpath(root, linux_build), mod))
    return alldrv_list

def get_kernel(check_dir):
    kernel = os.path.join(check_dir, "boot", "vmlinuz")
    if os.path.islink(kernel):
        kernel = os.readlink(kernel)
    if not os.path.exists(os.path.join(check_dir, "boot", os.path.basename(kernel))):
        kernel = max(glob.glob(os.path.join(check_dir, "boot", "vmlinuz-*")))
    kernel = os.path.basename(kernel)
    return kernel

def get_kernel_ver(check_dir):
    kernel = get_kernel(check_dir)
    kernel_pattern = re.compile(r"vmlinu[zx]-([0-9]\.[0-9]*\.[0-9]*-[0-9]*.*)")
    assert(kernel_pattern.match(kernel))
    mod_ver = kernel_pattern.search(kernel).group(1)
    return mod_ver

# TODO: use GRUB config
def get_initrd(check_dir):
    mod_ver = get_kernel_ver(check_dir)
    # Fedora
    initrd = os.path.join(check_dir, "boot", f"initramfs-{mod_ver}.img")
    if os.path.exists(initrd):
        return initrd
    # Ubuntu
    initrd = os.path.join(check_dir, "boot", f"initrd.img-{mod_ver}")
    if os.path.exists(initrd):
        return initrd

    initrd = os.path.join(check_dir, "boot", f"initrd-{mod_ver}")
    if os.path.exists(initrd):
        return initrd
    
    assert (False)
    return None

def get_target_info(check_dir):
    mod_ver = get_kernel_ver(check_dir)

    ## Modules Files
    mod_dir = os.path.join(check_dir, "lib/modules/", mod_ver)

    mod_list = set()
    with open(os.path.join(mod_dir, "modules.order"), 'r') as fd:
        for line in fd:
            mod_path = line.rstrip()
            mod_name = os.path.basename(mod_path)
            mod_name = re.sub("\.ko.*$", "", mod_name)
            mod_name = re.sub('-', '_', mod_name)
            mod_list.add((mod_name, '/' + mod_path))

#     for root, _, files in os.walk(mod_dir):
#         for fn in files:
#             m = builddep.norm_mod(fn)
#             if m.endswith(".ko"):
#                 m = m[:-3]
#                 mod_list.add((m, os.path.join(root[len(mod_dir):], fn)))

    symtab = []
    with open(os.path.join(check_dir, "boot", "System.map-"+mod_ver), 'r') as fd:
        data = fd.read().strip()
        for line in data.split('\n'):
            addr, ty, sym = line.split()
            symtab.append((int(addr,16), ty, sym))

    return mod_list, symtab

def load_db(hwconf, devdb_path, log=False):
    devlist = []
    with open(hwconf, 'r') as fd:
        data = fd.read().strip().split('\n')
        devlist = [sig.strip() for sig in data]

    devdb = dict()
    driver_map = dict()
    with open(devdb_path, 'r') as fd:
        data = fd.read().strip().split('\n')
        for line in data:
            ty,entry,mod,sig = line.strip().split()
            sig = sig.replace('*', '.*')
            sig = sig.replace('?', '.?')
            devdb[re.compile(sig)] = mod
            driver_map[mod] = entry

    modlist = []
    for key in devlist:
        found = False
        for sig in devdb:
            if sig.match(key):
                modlist.append(devdb[sig])
                found=True
                #break
        if not found:
            if log:
                print("Unknown device: ", key)
    return (devlist, devdb, driver_map, modlist)

def initcall_sym2init(sym):
    newsym = re.sub(r"__[0-9]+_[0-9]+_", '____', sym)
    if '____' not in newsym:
        if sym in ["__initcall_start", "__initcall_end"]:
            return None
        if not sym.startswith("__initcall_"):
            return None
        osym = sym[len("__initcall_"):]
    else:
        osym = newsym.split('____')[1]
    if osym[-1].isnumeric():
        osym = osym[:-1]
    if osym[-2].isnumeric() and osym[-1] == 's':
        osym = osym[:-2]
    if osym.endswith("early") and not osym.endswith("_early"):
        osym = osym[:-5]
    if osym.endswith("rootfs"):
        osym = osym[:-6]
    if osym.endswith("con"):
        osym = osym[:-3]
    return osym

def match_initcall_sig(mod, initf, sym):
    osym = sym
    if osym[-1].isnumeric():
        osym = osym[:-1]
    if osym[-2].isnumeric() and osym[-1] == 's':
        osym = osym[:-2]
    if osym.endswith("early") and not osym.endswith("_early"):
        osym = osym[:-5]
    if osym.endswith("rootfs"):
        osym = osym[:-6]
    if osym.endswith("con"):
        osym = osym[:-3]

    initcall_sig_old = "__initcall_"+initf
    mod = re.sub(r"-", '_', mod)
    initcall_sig = "__initcall__kmod_"+mod+"____"+initf
    newsym = re.sub(r"__[0-9]+_[0-9]+_", '____', sym)
    return newsym.startswith(initcall_sig) or osym == initcall_sig_old

def cache_load(p):
    if (os.path.exists(p)):
        with open(p, 'rb') as fd:
            return pickle.load(fd)
    return None

def cache_dump(obj, p):
    with open(p, 'wb') as fd:
        pickle.dump(obj, fd)

def check_rmf(f, mod, patched, fdeps, odeps, processed, \
        relmod_bypass_filter, relmod_filter, func_check):
    if f in processed:
        return (f in patched, {f} if (f in patched and ((not func_check) or func_check(f))) else {})
    processed.add(f)

    newpatched = set()
    bypasscnt = 0
    rmflag = fdeps and (f, mod) in fdeps and len(fdeps[(f, mod)]) > 0
    if not rmflag:
        return (False, {})
    for cf, cmod in fdeps[(f, mod)]:
        if cmod.endswith(".o"):
            if mod == cmod or cf in patched:
                continue
            else:
                rmflag, rmset = check_rmf(cf, cmod, patched|newpatched, odeps.related(cf), odeps, processed, \
                        relmod_bypass_filter, relmod_filter, func_check)
                newpatched.update(rmset)
                if not rmflag:
                    break
        else:
            # .ko
            m = re.sub('-', '_', os.path.basename(cmod).split('.')[0])
            if relmod_bypass_filter and relmod_bypass_filter(m):
                bypasscnt += 1
                continue
            if relmod_filter and relmod_filter(m):
                rmflag = False
                break
    return (rmflag, newpatched)

def check_fdep(fdep_checklist, patch_sym, odeps, \
        relmod_bypass_filter=None, relmod_filter=None, func_check=None, mod_check=None):
    rmfunc_fdep = set()
    rmko_fdep = set()

    processed = set()
    for f in fdep_checklist:
        fdeps = odeps.related(f)
        if not fdeps:
            continue
        for relf, relmod in fdeps:
            # check caller
            rmflag, rmset = check_rmf(relf, relmod, patch_sym|rmfunc_fdep, fdeps, odeps, processed, \
                    relmod_bypass_filter, relmod_filter, func_check)
            rmfunc_fdep.update(rmset)

            if not rmflag:
                continue
            if relmod.endswith(".o"):
                if func_check and func_check(relf):
                    continue
                if relf not in patch_sym:
                    rmfunc_fdep.add(relf)
            else:
                assert relmod.endswith(".ko")
                if mod_check and mod_check(relmod):
                    continue
                if relf not in patch_sym:
                    rmko_fdep.add((relf, relmod))
    return (rmfunc_fdep, rmko_fdep)

def check_drivers(hwconf, devdb_path, check_dir, busreg_apis, btobj_deps, linux_src, linux_build, cache="/tmp/.cache/forklift", log=False, tag=""):
    if not os.path.exists(cache):
        os.makedirs(cache, exist_ok=True)
    prev = time.time()
    devlist, devdb, driver_map, modlist = load_db(hwconf, devdb_path)
    if log:
        print("Load DB: ", time.time()-prev)
        prev = time.time()

    # all drivers db to check non-public drivers
    alldrv_list = cache_load(os.path.join(cache, "alldrv_list"))
    if not alldrv_list:
        alldrv_list = load_alldrv(linux_build)
        cache_dump(alldrv_list, os.path.join(cache, "alldrv_list"))
    if log:
        print("Load All Drv: ", time.time()-prev)
        prev = time.time()

    mod_dir = os.path.join(check_dir, "lib/modules/", get_kernel_ver(check_dir))
    mod_dep, rev_dep = builddep.get_deps(mod_dir)
    if log:
        print("Build Mod Dep: ", time.time()-prev)
        prev = time.time()

    allmod, symtab = get_target_info(check_dir)

    # non-function symbols
    nonfunc_syms = set([t[2] for t in symtab if t[1] not in ['t', 'T']])

    # All Mods on disk img
    alldiskmods = set([t[0] for t in allmod])
    diskmodmaps = dict()
    for mod, p in allmod:
        if mod not in diskmodmaps:
            diskmodmaps[mod] = set()
        if p.startswith('/'):
            p = p[1:]
        diskmodmaps[mod].add(p)

    mod_keeps = set()
    mod_remove = set()
    mod_remove_path = set()
    mod_exists = set()
    mod_unknown = set()
    for m, fpath in allmod:
        altm = re.sub('-', '_', m)
        if (m in driver_map or altm in driver_map) and (m not in modlist and altm not in modlist):
            mod_remove_path.add(fpath)
            mod_remove.add(m)
        elif m in modlist or altm in modlist:
            mod_keeps.add(m)
        if m in driver_map or altm in driver_map:
            mod_exists.add(m)
        if m not in alldrv_list and altm not in alldrv_list:
            mod_unknown.add(m)

    if log:
        print("mod_list: ", len(mod_exists), "/", len(modlist))
        print("mod_remove: ", len(mod_remove), "/", len(driver_map))
        print(mod_unknown)

    if log:
        print("Build Mod rm_list: ", time.time()-prev)
        prev = time.time()

    mod_keeps_update = set()
    for m in mod_keeps:
        if m not in mod_dep:
            continue
        for dm in mod_dep[m]:
            if dm in alldiskmods:
                mod_keeps_update.add(dm)
    mod_keeps.update(mod_keeps_update)
    ## Builtin Modules
    patch_list = set()
    skip_list = set()
    builtin_mod_remove = set()
    builtin_mod_exists = set()
    allkernfunc = set()
    start_flag = False
    for addr,ty,sym in symtab:
        if ty in ['T', 't']:
            allkernfunc.add(sym)
        if sym == '__initcall_start':
            start_flag = True
            continue
        if sym == '__con_initcall_end':
            break
        if start_flag:
            notfound = True
            for mod in driver_map:
                func = driver_map[mod]
                if match_initcall_sig(mod, func, sym):
                    builtin_mod_exists.add(mod)
                    if mod in modlist:
                        continue
                    if log:
                        print("native: ", sym, mod, func)
                    patch_list.add(sym)
                    builtin_mod_remove.add(mod)
                    notfound = False
                    break
            if notfound and (sym.startswith("__initcall__kmod_") or sym.startswith("__initcall_")):
                skip_list.add(sym)
    sym_map = {}
    for addr,_,sym in symtab:
        sym_map[sym] = addr
    if log:
        print("patch builtin list: ", len(patch_list))
        print("skip builtin list: ", len(skip_list))

    # Count all existing Builtin Modules
    allbuiltin = patch_list.copy()
    for m in driver_map:
        func = driver_map[m]
        for sym in skip_list:
            if match_initcall_sig(m, func, sym):
                allbuiltin.add(sym)
                break

    if log:
        print("Build Built-in rm_list: ", time.time()-prev)
        prev = time.time()

    # Mod Deps
    new_mod_remove = mod_remove.copy()
    for m in mod_remove:
        if m in rev_dep:
            new_mod_remove.update([x for x in rev_dep[m] if x in alldiskmods])

    # Builtin Deps
    new_patch_list = patch_list.copy()
    new_builtin_mod_remove = builtin_mod_remove.copy()
    for m in builtin_mod_remove:
        if m in rev_dep:
            for dep in rev_dep[m]:
                func = ""
                if dep in driver_map:
                    func = driver_map[dep]
                for sym in skip_list:
                    if match_initcall_sig(dep, func, sym):
                        new_patch_list.add(sym)
                        new_builtin_mod_remove.add(dep)
                        break

    # Mod Deps over Builtin
    new_new_mod_remove = new_mod_remove.copy()
    for m in new_builtin_mod_remove:
        if m in rev_dep:
            new_new_mod_remove.update([x for x in rev_dep[m] if x in alldiskmods])

    if log:
        print("Build Deps rm_list: ", time.time()-prev)
        prev = time.time()

    # Total Mods with Deps
    new_mod_exists = mod_exists.copy()

    # Mod has no init
    noentry = cache_load(os.path.join(cache, "noentry"+tag))
    if not noentry:
        noentry = checkmodsym.get_noentry(mod_dir)
        cache_dump(noentry, os.path.join(cache, "noentry"+tag))
    full_rev_dep = cache_load(os.path.join(cache, "full_rev_dep"+tag))
    if not full_rev_dep:
        full_rev_dep = checkmodsym.get_deps(mod_dir)
        cache_dump(full_rev_dep, os.path.join(cache, "full_rev_dep"+tag))
    dep_remove = set()
    for m in noentry:
        if os.path.basename(m).split('.')[0] not in alldiskmods:
            continue
        if m in full_rev_dep and set([os.path.basename(x).split('.')[0] for x in full_rev_dep[m]]).intersection(alldiskmods).issubset(new_new_mod_remove):
            dep_remove.add(m)
    if log:
        print("NoEntry Mod Dep Remove: ", len(dep_remove), len(set([os.path.basename(x).split('.')[0] for x in dep_remove]).difference(new_new_mod_remove)))
        print(dep_remove)

    if log:
        print("Build NoEntry Deps rm_list: ", time.time()-prev)
        prev = time.time()
    cur_removed_mods = set([os.path.basename(x).split('.')[0] for x in dep_remove]) | new_new_mod_remove

    # Function Dependency -- Built-in && Register APIs
    rmfunc_fdep = set()
    rmko_fdep = set()
    odeps = cache_load(os.path.join(cache, "objdeps"))
    if not odeps:
        odeps = gen_objdep.ObjDeps(linux_src, linux_build, btobj_deps)
        cache_dump(odeps, os.path.join(cache, "objdeps"))
    fdep_checklist = set()
    # - collect functions of built-in modules
    patch_sym = set([initcall_sym2init(x) for x in new_patch_list])
    fdep_checklist.update(patch_sym)
    # - collect registration APIs
    fdep_checklist.update(busreg_apis)
    # - collect import symbols from removed .ko
    mod_removed = dep_remove.copy()
    for m in cur_removed_mods:
        mod_removed.update([os.path.join(mod_dir, p) for p in diskmodmaps[m]])
    for m in mod_removed:
        if os.path.exists(m):
            fdep_checklist.update(checkmodsym.get_sym(m, ['U', 'u']))

    def relmod_bypass_filter(mod):
        return mod not in new_mod_exists and mod not in builtin_mod_exists
    def relmod_filter(mod):
        if mod in mod_keeps:
            return True
        if mod not in cur_removed_mods and mod not in new_builtin_mod_remove:
            return True
        return False
    def func_check(func):
        return func not in sym_map or func in nonfunc_syms
    def mod_check(mod):
        return os.path.basename(mod).split('.')[0] not in diskmodmaps or \
                os.path.basename(mod).split('.')[0] in cur_removed_mods

    rmfunc_fdep, rmko_fdep = check_fdep(fdep_checklist, patch_sym, odeps, \
            relmod_bypass_filter, relmod_filter, func_check, mod_check)

    for relf, relmod in rmko_fdep:
        if relmod in builtin_mod_exists:
            rmfunc_fdep.add(relf)

    return (new_mod_exists, mod_remove, mod_unknown, patch_list, allmod, allbuiltin, skip_list.union(patch_list), new_mod_remove.difference(mod_remove), new_patch_list.difference(patch_list), new_new_mod_remove.difference(new_mod_remove), set([os.path.basename(x).split('.')[0] for x in dep_remove]).difference(new_new_mod_remove), None, None, rmfunc_fdep, rmko_fdep, allkernfunc, builtin_mod_exists, new_builtin_mod_remove)


def patch_kernel(img_mounted, patch_list, filter_key=None, extra=[]):
    extract_vmlinux='./extract-vmlinux'
    if not os.path.exists(extract_vmlinux):
        os.system(f"wget https://raw.githubusercontent.com/torvalds/linux/master/scripts/extract-vmlinux -O {extract_vmlinux}")
        stat = os.stat(extract_vmlinux)
        os.chmod(extract_vmlinux, st.st_mode | stat.S_IEXEC)

    # find and decompress vmlinuz
    mod_ver = get_kernel_ver(img_mounted)
    config = os.path.join(img_mounted, "boot", "config-"+mod_ver)
    vmlinuz = os.path.join(img_mounted, "boot", get_kernel(img_mounted))
    _, vmlinux = tempfile.mkstemp()
    with open(vmlinux, 'w') as f:
        subprocess.call([extract_vmlinux, vmlinuz], stdout=f)

    # load sym_map
    sym_tab = get_target_info(img_mounted)[1]
    sym_map = dict()
    for addr,_,sym in sym_tab:
        sym_map[sym] = addr

    patch_set = dict()
    for sym in patch_list|set(extra):
        if sym.startswith("__initcall_"):
            osym = initcall_sym2init(sym)
        else:
            osym = sym
            if filter_key and True in [t in sym for t in filter_key]:
                continue
        if osym not in sym_map:
            continue
        patch_set[osym] = sym_map[osym] - sym_map['_text']

    prev_time = time.time()

    patch_ranges = list()
    kern_text_off, kern_text_va = disasm.get_text_rel(vmlinux)
    for sym in patch_set:
        off = patch_set[sym]
        patch_ranges.append((sym, disasm.disasm(vmlinux, off, text_rel=(kern_text_off, kern_text_va))))

    with open(vmlinux, 'rb') as fd:
        data = bytearray(fd.read())

    for sym, patch_range in patch_ranges:
        if not patch_range:
            continue
        for poff in patch_range:
            plen = patch_range[poff]
            if data[poff] == 0xe8: # Ftrace Stub
                poff += 5
                plen -= 5
            if data[poff] == 0xf3 and data[poff+1] == 0x0f and data[poff+2] == 0x1e and data[poff+3] == 0xfa:
                poff += 4
                plen -= 4

            if plen > 0:
                data[poff] = 0xc3
                for pi in range(1, plen):
                    data[poff+pi] = 0x90

    with open(vmlinux+'.patched', 'wb') as outfd:
        outfd.write(data)

    return vmlinux+'.patched'

def run_kernel_cmd(cmdfile, cwd):
    cmdfile = os.path.join(cwd, cmdfile)
    print("DEBUG run_kernel_cmd ", cmdfile)
    with open(cmdfile, 'r') as fd:
        data = fd.read().strip()
        for line in data.split('\n'):
            line = line.strip()
            if not line.startswith("cmd_"):
                continue
            cur_cwd = os.getcwd()
            os.chdir(cwd)
            os.system(line.split(':=')[1].strip())
            os.chdir(cur_cwd)

unpack_helper = {
        "zst" : "zstdcat",
        "gz"  : "zcat",
        "bz2" : "bzcat",
        "xz"  : "xzcat",
        "lzma": "lzcat",
        "lz4" : "lz4cat",
        "lzo" : "lzop -fdc",
        }
pack_helper = {
        "zst" : "zstd",
        "gz"  : "gzip",
        "bz2" : "bzip2",
        "xz"  : "xz",
        "lzma": "lzma",
        "lz4" : "lz4",
        "lzo" : "lzop",
        }
def patch_initrd(check_dir, rmmods, filter_key=[], opensuse_fstab_patch=False):
    initrd = get_initrd(check_dir)
    ker_ver = get_kernel_ver(check_dir)
    tmprd = tempfile.mkdtemp(prefix='ramfs_')
    cur_cwd = os.getcwd()
    os.chdir(tmprd)

    os.system(f"{os.path.join(CURDIR, '../utils/unpack-initramfs.sh')} {initrd}")
    fspart = None
    parts = None
    for _,_,files in os.walk('./out'):
        parts = [None] * len(files)
        for f in files:
            ext = f.split('.')[-1]
            idx = None
            if ext in unpack_helper:
                newf = f[:-len(ext)-1]
                assert (newf.endswith(".cpio"))
                idx = int(newf[:-5].split('-')[-1])-1
            else:
                assert (f.endswith(".cpio"))
                idx = int(f[:-5].split('-')[-1])-1
            parts[idx] = f
            if ext in unpack_helper:
                fspart = f
                break
    if not fspart:
        fspart = parts[-1]
    unpackdir = "unpack"
    if os.path.exists(unpackdir):
        shutil.rmtree(unpackdir)
    os.mkdir(unpackdir)
    os.chdir(unpackdir)
    os.system(f"({unpack_helper[f.split('.')[-1]]} | cpio -id) < {os.path.join('../out', fspart)}")
    if filter_key:
        rmmods = [m for m in rmmods if True not in [fk in m for fk in filter_key]]
    stat_res = calc_module_count(".", rmmods, ker_ver)
    remove_module('.', rmmods, ker_ver)
    if opensuse_fstab_patch:
        with open("./etc/fstab", 'w') as fd:
            fd.write("LABEL=ROOT /sysroot xfs defaults 0 1\n")
            fd.write("LABEL=EFI /boot/efi vfat defaults 0 0\n")
    os.system(f"find .|cpio -o -H newc|{pack_helper[f.split('.')[-1]]} > ../newrd.img")
    os.chdir("..")
    data = b""
    for p in parts:
        if p == fspart:
            p = "newrd.img"
        else:
            p = os.path.join("out", p)
        with open(p, 'rb') as fd:
            data += fd.read()
    with open(os.path.join(cur_cwd, initrd), 'wb') as fd:
        fd.write(data)

    os.chdir(cur_cwd)

    return stat_res

def patch_module (check_dir, patch_list, mod_ver=None):
    # reorganize patch list
    mod_patch = {}
    for sym, mod in patch_list:
        mod = os.path.basename(mod).split('.')[0]
        if mod not in mod_patch:
            mod_patch[mod] = set()
        mod_patch[mod].add(sym)

    prev_time = time.time()

    # Load target modules and start patching
    if not mod_ver:
        mod_ver = get_kernel_ver(check_dir)
    mod_dir = os.path.join(check_dir, "lib/modules/", mod_ver)
    symoffpat = re.compile(r".*<(.*)> \(File Offset: (.*)\):$")
    for root,_, mods in os.walk(mod_dir):
        for mod in mods:
            m = mod.split('.')[0]
            ext = mod.split('.')[-1]

            if m in mod_patch:
                # unpack module
                workdir = tempfile.mkdtemp(prefix="fdepmod_")
                target_mod = os.path.join(workdir, m+".ko")
                if ext == "ko":
                    shutils.copy2(os.path.join(root, mod), target_mod)
                else:
                    os.system(f"{unpack_helper[ext]} < {os.path.join(root, mod)} > {target_mod}")

                # build offset map
                out = subprocess.check_output(f"objdump -dF {target_mod} | grep '):$'", shell=True)
                off_map = {}
                for line in out.decode('latin-1').split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    pat = re.match(symoffpat, line)
                    sym, off = pat.group(1, 2)
                    off_map[sym] = int(off, 16)

                # patch module
                with open(target_mod, 'rb') as fd:
                    kodata = list(fd.read())
                for patchsym in mod_patch[m]:
                    if patchsym not in off_map:
                        continue
                    patchoff = off_map[patchsym]
                    base_off = patchoff
                    patch_range = disasm.disasm(target_mod, patchoff, True)
                    ret_patched = False
                    for poff in patch_range:
                        plen = patch_range[poff]
                        if not ret_patched:
                            # Skip Ftrace Stub
                            if kodata[poff:poff+5] == list(b'\xe8\x00\x00\x00\x00'):
                                poff += 5
                                plen -= 5
                            if plen > 0:
                                kodata[poff] = 0xc3
                                for pi in range(1, plen, 1):
                                    kodata[poff+pi] = 0x90
                                ret_patched = True
                            else:
                                pass    # try next time
                        else:
                            for pi in range(plen):
                                kodata[poff+pi] = 0x90
                    assert (ret_patched)
                # Write back
                with open(target_mod, 'wb') as outfd:
                    outfd.write(bytes(kodata))

                if ext == "ko":
                    # os.system(f"cp {target_mod} {os.path.join(root, mod)}")
                    print(f"cp {target_mod} {os.path.join(root, mod)}")
                else:
                    # os.system(f"{pack_helper[ext]} < {target_mod} > {os.path.join(root, mod)}")
                    print(f"{pack_helper[ext]} < {target_mod} > {os.path.join(root, mod)}")

                shutil.rmtree(workdir)

    print("Patch modules: ", time.time()-prev_time)

def remove_module(check_dir, rmmods, mod_ver=None):
    ## Remove Drivers in RootFS
    if not mod_ver:
        mod_ver = get_kernel_ver(check_dir)
    mod_dir = os.path.join(check_dir, "lib/modules/", mod_ver)
    for root,_, mods in os.walk(mod_dir):
        for mod in mods:
            m = mod.split('.')[0]
            if m in rmmods or re.sub('-', '_', m) in rmmods:
                drv_path = os.path.join(root, mod)
                os.unlink(drv_path)
#                os.rename(drv_path, drv_path + '.hacksawed')

    os.system(f"depmod -a -b {check_dir} {mod_ver}")
    

def calc_module_size(check_dir, rmmods, mod_ver=None):
    ## Remove Drivers in RootFS
    if not mod_ver:
        mod_ver = get_kernel_ver(check_dir)
    total_size = 0
    mod_dir = os.path.join(check_dir, "lib/modules/", mod_ver)
    for root,_, mods in os.walk(mod_dir):
        for mod in mods:
            m = mod.split('.')[0]
            if m in rmmods or re.sub('-', '_', m) in rmmods:
                drv_path = os.path.join(root, mod)
                total_size += os.path.getsize(drv_path)
    return total_size

def calc_module_count(check_dir, rmmods, mod_ver=None):
    ## Remove Drivers in RootFS
    if not mod_ver:
        mod_ver = get_kernel_ver(check_dir)
    total_cnt = 0
    rm_cnt = 0
    mod_dir = os.path.join(check_dir, "lib/modules/", mod_ver)
    for root,_, mods in os.walk(mod_dir):
        for mod in mods:
            if 'ko' not in mod.split('.'):
                continue
            m = mod.split('.')[0]
            total_cnt += 1
            if m in rmmods or re.sub('-', '_', m) in rmmods:
                rm_cnt += 1
    return (rm_cnt, total_cnt)

def replace_kernel(check_dir, newkern):
    kern = get_kernel(check_dir)
    shutil.copy2(newkern, os.path.join(check_dir, 'boot', kern))

if __name__ == '__main__':
    sys.exit(0)
