#!/usr/bin/env python3

import os
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
    #print(kernel)
    assert(kernel_pattern.match(kernel))
    mod_ver = kernel_pattern.search(kernel).group(1)
    return mod_ver

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
    for root, _, files in os.walk(mod_dir):
        for fn in files:
            m = builddep.norm_mod(fn)
            if m.endswith(".ko"):
                m = m[:-3]
                mod_list.add((m, os.path.join(root[len(mod_dir):], fn)))

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
            devdb[re.compile(sig)] = re.sub(r"-", '_', mod)
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

    # Build Module dependencies
    mod_dep = cache_load(os.path.join(cache, "mod_dep"))
    rev_dep = cache_load(os.path.join(cache, "rev_dep"))
    if not mod_dep or not rev_dep:
        mod_dep, rev_dep = builddep.get_deps(linux_build)
        cache_dump(mod_dep, os.path.join(cache, "mod_dep"))
        cache_dump(rev_dep, os.path.join(cache, "rev_dep"))
    if log:
        print("Build Mod Dep: ", time.time()-prev)
        prev = time.time()

    allmod, symtab = get_target_info(check_dir)

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
    mod_dir = os.path.join(check_dir, "lib/modules/", get_kernel_ver(check_dir))
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

    # Core Module Discovery & Removal
    core_mod_remove = set()
    core_mod_dep_remove = set()
    coredepmap = cache_load(os.path.join(cache, "coredepmap"+tag))
    if not coredepmap:
        coredepmap = builddep.get_core_deps(mod_dir, driver_map, busreg_apis)
        cache_dump(coredepmap, os.path.join(cache, "coredepmap"+tag))
    sub_rev_dep = dict()
    for m in full_rev_dep:
        mod = os.path.basename(m).split('.')[0]
        if mod not in sub_rev_dep:
            sub_rev_dep[mod] = set()
        sub_rev_dep[mod].update([os.path.basename(d).split('.')[0] for d in full_rev_dep[m]])
    for core in coredepmap:
        if core not in alldiskmods:
            continue
        if coredepmap[core] and coredepmap[core].intersection(alldiskmods).issubset(cur_removed_mods):
            if core in cur_removed_mods:
                continue
            core_mod_remove.add(core)
            if core in sub_rev_dep:
                core_mod_dep_remove.update([x for x in sub_rev_dep[core] if x in alldiskmods and x not in cur_removed_mods])

    if log:
        print("Build Core Module Deps rm_list: ", time.time()-prev)
        prev = time.time()
    cur_removed_mods.update(core_mod_remove)
    cur_removed_mods.update(core_mod_dep_remove)

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

    for f in fdep_checklist:
        fdeps = odeps.related(f)
        if not fdeps:
            continue
        for relf, relmod in fdeps:
            rmflag = True
            for cf, cmod in fdeps[(relf, relmod)]:
                if cmod.endswith(".o"):
                    if relmod == cmod or cf in (patch_sym|rmfunc_fdep):
                        continue
                    else:
                        rmflag = False
                        break
                mod = os.path.basename(cmod).split('.')[0]
                if mod not in new_mod_exists and mod not in builtin_mod_exists:
                    continue
                rmflag = rmflag and ((mod in cur_removed_mods) or (mod in new_builtin_mod_remove))

            if not rmflag:
                continue
            if relmod.endswith(".o"):
                if relf not in sym_map:
                    continue
                if relf not in patch_sym:
                    rmfunc_fdep.add(relf)
            else:
                assert relmod.endswith(".ko")
                if os.path.basename(relmod).split('.')[0] not in diskmodmaps:
                    continue
                if relf not in patch_sym and os.path.basename(relmod).split('.')[0] not in cur_removed_mods:
                    rmko_fdep.add((relf, relmod))

    return (new_mod_exists, mod_remove, mod_unknown, patch_list, allmod, allbuiltin, skip_list.union(patch_list), new_mod_remove.difference(mod_remove), new_patch_list.difference(patch_list), new_new_mod_remove.difference(new_mod_remove), set([os.path.basename(x).split('.')[0] for x in dep_remove]).difference(new_new_mod_remove), core_mod_remove, core_mod_dep_remove, rmfunc_fdep, rmko_fdep, allkernfunc, builtin_mod_exists, new_builtin_mod_remove)


def patch_builtin(vmlinux, patch_list, sym_tab):
    # load sym_map
    sym_map = dict()
    for addr,_,sym in sym_tab:
        sym_map[sym] = addr

    patch_set = dict()
    for sym in patch_list:
        #print(sym)
        if sym.startswith("__initcall_"):
            osym = initcall_sym2init(sym)
        else:
            osym = sym
        if osym not in sym_map:
            continue
        patch_set[osym] = sym_map[osym] - sym_map['_text']

    prev_time = time.time()

    patch_range = dict()
    kern_text_off, kern_text_va = disasm.get_text_rel(vmlinux)
    with open(vmlinux, 'rb') as fd:
        data = list(fd.read())
        for sym in patch_set:
            off = patch_set[sym]
            patch_range.update(disasm.disasm(vmlinux, off, text_rel=(kern_text_off, kern_text_va)))
    print("Patch kernel - disasm : ", time.time()-prev_time)
    prev_time = time.time()

    ret_patched = False
    for poff in patch_range:
        plen = patch_range[poff]
        if not ret_patched:
            # Skip Ftrace Stub
            if data[poff] == 0xe8:
                poff += 5
                plen -= 5
            if plen > 0:
                data[poff] = 0xc3
                for pi in range(1, plen, 1):
                    data[poff+pi] = 0x90
                ret_patched = True
            else:
                pass    # try next time
        else:
            for pi in range(plen):
                data[poff+pi] = 0x90
    assert (ret_patched)
    with open(vmlinux+'.patched', 'wb') as outfd:
        outfd.write(bytes(data))

    print("Patch kernel: ", time.time()-prev_time)
    return vmlinux+'.patched'

def run_host(cmd, cwd=None, docker=False):
    if docker:
        workdir = "/data"
        if cwd:
            workdir = os.path.join(workdir, cwd)
        os.system(f'docker run --rm -it -v $PWD:/data -w {workdir} -u $(id -u $USER):$(id -g $USER) kernelbuild bash -c "{cmd}"')
    else:
        if cwd:
            cur_cwd = os.getcwd()
            os.chdir(cwd)
        os.system(cmd)
        if cwd:
            os.chdir(cur_cwd)

def run_kernel_cmd(cmdfile, cwd='./build'):
    cmdfile = os.path.join(cwd, cmdfile)
    print("DEBUG run_kernel_cmd ", cmdfile)
    with open(cmdfile, 'r') as fd:
        data = fd.read().strip()
        for line in data.split('\n'):
            line = line.strip()
            if not line.startswith("cmd_"):
                continue
            run_host(line.split(':=')[1].strip(), cwd=cwd)

def repack_kernel(img_mounted, linux_build, patchcb=None):
    vmlinuz = os.path.join(img_mounted, "boot", get_kernel(img_mounted))
    vmlinux = os.path.join('/tmp', 'vmlinux.unpack')

    mod_ver = get_kernel_ver(img_mounted)
    mod_ver_min = mod_ver.split('-')[0]
    if mod_ver_min[-2:] == '.0':
        mod_ver_min = mod_ver_min[:-2]
    config = os.path.join(img_mounted, "boot", "config-"+mod_ver)

    os.system(f"{CURDIR}/../kernel/prepare_bzimage.sh {mod_ver_min} {config}")
    os.system(f"{CURDIR}/../kernel/src/linux-{mod_ver_min}/scripts/extract-vmlinux {vmlinuz} > {vmlinux}")

    return

    if patchcb:
        vmlinux = patchcb(vmlinux)

    cur_cwd = os.getcwd()

    os.chdir(os.path.join(workdir, 'linux-stable'))
    os.system("git checkout .")
    git_ver = subprocess.check_output(["git", "describe", "--tag"]).strip()
    if git_ver.decode('latin-1') != branch_ver:
        os.system("rm -rf build")
    os.system("mkdir -p build")
    os.system(f"git checkout {branch_ver}")
    # Fixups
    if branch_ver == "v5.10":
        os.system(f"git apply {os.path.join(CURDIR, '0004-x86-entry-build-thunk_-BITS-only-if-CONFIG_PREEMPTION-y.patch')}")
    # - Fixup Pahole(?)
    os.system("mv scripts/link-vmlinux.sh scripts/link-vmlinux.sh_bak")
    with open('scripts/link-vmlinux.sh_bak', 'r') as fd:
        lkscript = fd.read()
    with open('scripts/link-vmlinux.sh', 'w') as fd:
        patchsig = 'vmlinux_link ${1}\n'
        if patchsig in lkscript:
            idx = lkscript.find(patchsig)+len(patchsig)
            with open(os.path.join(CURDIR, 'pahole.patch'), 'r') as pfd:
                patches = pfd.read().strip().split('>---<')
                for pt in patches[::-1]:
                    if pt.strip().split('\n')[0].strip() not in lkscript:
                        lkscript = lkscript[:idx] + '\n' + pt + '\n' + lkscript[idx:]
            idx = lkscript.find('LLVM_OBJCOPY=', idx)
            idx = lkscript.find('-J ', idx)
            idx += 3
            lkscript = lkscript[:idx] + '${hacksaw_extra_paholeopt} ' + lkscript[idx:]
        fd.write(lkscript)
    os.system(f"cp {config} ./build/.config")

    # disable module signing
    os.system("sed -i 's/^CONFIG_MODULE_SIG_KEY.*//' ./build/.config")
    os.system("sed -i 's/^CONFIG_SYSTEM_TRUSTED_KEY.*//' ./build/.config")
    os.system("sed -i 's/^CONFIG_SYSTEM_REVOCATION_.*//' ./build/.config")
    #os.system("sed -i 's/^CONFIG_DEBUG_INFO_BTF.*//' ./build/.config")

    run_host("make olddefconfig O=./build")
    run_host("cat ./build/.config.old | grep CONFIG_VERSION_SIGNATURE >> ./build/.config")
    run_host("make -j4 O=./build kernel bzImage")

    # repacking
    os.system(f"cat {vmlinux}|gzip -n -f -9 > build/arch/x86/boot/compressed/vmlinux.bin.gz")    # ./build/arch/x86/boot/compressed/.vmlinux.bin.gz.cmd
    run_kernel_cmd("./arch/x86/boot/compressed/.piggy.S.cmd")
    run_kernel_cmd("./arch/x86/boot/compressed/.piggy.o.cmd")
    run_kernel_cmd("./arch/x86/boot/compressed/.vmlinux.cmd")
    run_kernel_cmd("./arch/x86/boot/.vmlinux.bin.cmd")
    run_kernel_cmd("./arch/x86/boot/.header.o.cmd")
    run_kernel_cmd("./arch/x86/boot/.setup.elf.cmd")
    run_kernel_cmd("./arch/x86/boot/.setup.bin.cmd")
    run_kernel_cmd("./arch/x86/boot/.bzImage.cmd")

    os.chdir(cur_cwd)

    os.system(f"cp {os.path.join(workdir, 'linux-stable/build/arch/x86/boot/bzImage')} {os.path.join(workdir, 'bzImage')}")
    return os.path.join(workdir, 'bzImage')

def patch_rootinit(check_dir, newinit):
    workdir = "./repack"
    init = os.path.join(check_dir, "sbin/init")
    if not os.path.exists(init):
        init = os.path.join(check_dir, "etc/init")
        if not os.path.exists(init):
            init = os.path.join(check_dir, "bin/init")
            assert (os.path.exists(init))

    root_init = os.path.join(check_dir, "init")
    if os.path.exists(root_init):
        init = root_init
    else:
        os.system(f"echo 'exec {os.path.relpath(init, check_dir)}' > {root_init}")
        os.system(f"chmod 777 {root_init}")

    init_dir = os.path.dirname(init)
    staged_init = os.path.join(init_dir, "staged_init")

    os.system(f"mv {init} {staged_init}")
    os.system(f"cp {newinit} {init}")
    os.system(f"chmod 777 {init}")


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
    tmprd = os.path.join("/tmp", initrd, "ramfs")
    if os.path.exists(tmprd):
        os.system(f"sudo rm -rf {tmprd}")
    os.system(f"mkdir -p {tmprd}")
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
    remove_firmware('.')
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

def patch_gdb_builtin(patch_list, sym_tab):
    # load sym_map
    sym_map = dict()
    for addr,_,sym in sym_tab:
        sym_map[sym] = addr

    # Patching
    import subprocess
    import signal

    def dbgsendline(p, cmd):
        p.stdin.write(cmd+b'\n')
        p.stdin.flush()

    def dbgread(p):
        out = []
        banner = dbg.stdout.read(6)
        while banner != b'(gdb) ':
            line = dbg.stdout.readline()
            out.append(banner+line)
            print(banner+line)
            banner = dbg.stdout.read(6)
        return out

    ## builtin patch
    #qemu = subprocess.Popen(['./runguest.sh'], stdout=subprocess.DEVNULL)
    qemu_cmd = ['./qemu/build/qemu-system-x86_64',
            '-m', '2048', '-kernel', './vmlinuz', '-initrd', './initrd.img',
            '-append', '"console=ttyS0 nokaslr"',
            '-display', 'none', '-serial', 'stdio', '-monitor', 'none',
            '-s', '-S']
    #qemu = subprocess.Popen(qemu_cmd)
    dbg = subprocess.Popen(['gdb', '-q'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    dbgsendline(dbg, b'target remote :1234')
    dbgread(dbg)
    dbgsendline(dbg, b'c')
    time.sleep(2)   # NOTE: Timing is critical here. Some initcalls might be overwritten during bootstrap
    dbgread(dbg)
    dbg.send_signal(signal.SIGINT)
    dbgread(dbg)

    patch_set = dict()
    diff = set(patch_list)
    for sym in diff:
        print(sym)
        newsym = re.sub(r"__[0-9]+_[0-9]+_", '____', sym)
        osym = newsym.split('____')[1]
        if osym[-1].isnumeric():
            osym = osym[:-1]
        if osym[-2].isnumeric() and osym[-1] == 's':
            osym = osym[:-2]
        if osym.endswith("early"):
            osym = osym[:-5]
        if osym.endswith("rootfs"):
            osym = osym[:-6]
        print(hex(sym_map[osym]), osym)

        # Dump & Generate Signature
        dbgsendline(dbg, b'x/15xb ' + f'{hex(sym_map[osym])}'.encode('latin-1'))
        output = dbgread(dbg)
        addr = output[0].split()[0]
        sig = output[0].strip().split()[1:] + output[1].strip().split()[1:]
        print(addr, sig)
        sig = sig[5:]   # Ignore 5 bytes FTrace Stub
        print(sig)
        offset = int(addr[:-1], 16) & 0xffff    # Use 16 bits offset
        print(hex(offset))
        patch_set[osym] = (offset, b''.join([chr(int(x,16)).encode('latin-1') for x in sig]))

        dbgsendline(dbg, b'x/10i ' + f'{hex(sym_map[osym])}'.encode('latin-1'))
        dbgread(dbg)

    #qemu.terminate()
    #qemu.wait()

    # Match & Patch the Unpacked vmlinux kernel
    with open('./vmlinux.unpack', 'rb') as fd:
        data = fd.read()
        for sym in patch_set:
            off, sig = patch_set[sym]
            print(sym, [hex(c) for c in sig], sig)
            #print(len(re.findall(sig, data)))
            search = data.find(sig)
            print(hex(search), hex(off))
            while search != -1:
                if off+5 == (search&0xffff):
                    print("patch: ", sym, f" ({hex(search)}), {hex(sym_map[sym])}, {hex(sym_map[sym]+5-search)}")
                    print(hex(sym_map[sym] - sym_map['_text'] + 0x400000))
                    data = data[:search] + b'\xc3' + data[search+1:]
                search = data.find(sig, search+len(sig))

        with open('new_vmlinux', 'wb') as outfd:
            outfd.write(data)
    #exit(0)

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
                    os.system(f"cp {os.path.join(root, mod)} {target_mod}")
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

                os.system(f"rm -rf {workdir}")

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
                print('rm -rf', drv_path)
#                os.unlink(drv_path)

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

def remove_firmware(check_dir):
    # TODO: use modinfo
    return

def replace_kernel(check_dir, newkern):
    kern = get_kernel(check_dir)
    os.system(f"cp {newkern} {os.path.join(check_dir, 'boot', kern)}")

if __name__ == '__main__':
    sys.exit(0)
