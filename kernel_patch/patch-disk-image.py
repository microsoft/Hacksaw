#!/usr/bin/env python3

import os
import sys
import time
import pickle
import psutil
import subprocess
import multiprocessing
import tempfile
from argparse import ArgumentParser, Namespace

import hwfilter

CURDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURDIR, "..", "dependency"))
import gen_objdep

def parse_arguments(cli_args = None):
    parser = ArgumentParser(description='Run Driver Removal Pass')
    parser.add_argument('-k', '--kernel-path', action='store', required=True,
                        help='kernel source path')
    parser.add_argument('-b', '--kernel-build', action='store', required=True,
                        help='kernel build path')
    parser.add_argument('-i', '--disk-image', action='store', required=True,
                        help='disk image path')
    parser.add_argument('-p', '--hw-profile', action='store', required=True,
                        help='hardware profile')
    parser.add_argument('-d', '--db-path', action='store', required=True,
                        help='directory to find dependency DBs')
    parser.add_argument('-o', '--output-path', action='store', required=True,
                        help='output path')
    parser.add_argument('-s', '--system-map', action='store',
                        help='system.map file path')
    parser.add_argument('-g', '--guestmount', action='store_true',
                        help='use guestmount to access disk image')
    parser.set_defaults(guestmount=False)
    return parser.parse_args(args=cli_args)

def unmount_image(img_mounted):
    try:
        subprocess.run(['guestunmount', img_mounted], check=True)
        print(f"umounting {img_mounted}")
        pidfile = os.path.basename(img_mounted)+".pid"
        with open(pidfile, 'r') as fd:
            pid = int(fd.read())
        while psutil.pid_exists(pid):
            time.sleep(1)
        os.unlink(pidfile)
        os.rmdir(img_mounted)
    except subprocess.CalledProcessError:
        return False
    return True


def mount_image(diskimg):
    mntpoint = tempfile.mkdtemp()
    unmount_image(mntpoint)

    print(f"mounting {diskimg}")

    if os.path.basename(diskimg) == "suse.raw":
        os.system(f"guestmount -a {diskimg} --rw -m /dev/sda2 --pid-file {os.path.basename(mntpoint)}.pid {mntpoint}")
    else:
        os.system(f"guestmount -a {diskimg} --rw -i --pid-file {os.path.basename(mntpoint)}.pid {mntpoint}")

    return mntpoint

def analyze_image(img_mounted, busreg_apis, btobj_deps, linux_src, linux_build, dev, db, sysmap):
    db_match = set()
    rm = set()
    unk = set()
    bi_rm = set()
    allmod = set()
    bi_match = set()
    allbuiltin = set()
    mod_dep = set()
    builtin_dep = set()
    mod_builtin_dep = set()
    noentry = set()
    fdep_func = set()
    fdep_ko = set()
    allkernfunc = set()

    tup = hwfilter.check_drivers(dev, db, img_mounted, busreg_apis, btobj_deps, linux_src, linux_build, sysmap)

    db_match.update(tup[0])
    rm.update(tup[1])
    unk.update(tup[2])
    bi_rm.update(tup[3])
    allmod.update(tup[4])
    bi_match.update(tup[5])
    allbuiltin.update(tup[6])
    mod_dep.update(tup[7])
    builtin_dep.update(tup[8])
    mod_builtin_dep.update(tup[9])
    noentry.update(tup[10])
    fdep_func.update(tup[13])
    fdep_ko.update(tup[14])
    allkernfunc.update(tup[15])
    allbtdrv = tup[16]
    rmbtdrv = tup[17]

    return (db_match, rm, unk, bi_rm, allmod, bi_match, allbuiltin, mod_dep, builtin_dep, mod_builtin_dep, noentry,  fdep_func, fdep_ko, allkernfunc, allbtdrv, rmbtdrv)


def patch_image(img_mounted, rm, bi_rm, mod_dep, builtin_dep, mod_builtin_dep, noentry, fdep_func, fdep_ko, linux_build, sysmap):
#     print('rm:', len(rm))
#     print('bi_rm:', len(bi_rm))
#     print('mod_dep:', len(mod_dep))
#     print('builtin_dep:', len(builtin_dep))
#     print('mod_builtin_dep:', len(mod_builtin_dep))
#     print('noentry:', len(noentry))
#     print('fdep_func:', len(fdep_func))
#     print('fdep_ko:', len(fdep_ko))

    newkern = hwfilter.patch_kernel(img_mounted, bi_rm|builtin_dep|fdep_func, sysmap)
    hwfilter.replace_kernel(img_mounted, newkern)
    hwfilter.remove_module(img_mounted, rm|mod_dep|mod_builtin_dep|noentry)
    hwfilter.patch_module(img_mounted, fdep_ko)
    hwfilter.patch_initrd(img_mounted, rm|mod_dep|mod_builtin_dep|noentry)

    return

if __name__ == '__main__':
    args = parse_arguments()

    linux_src = args.kernel_path
    linux_build = args.kernel_build
    hwprof = args.hw_profile
    diskimg = args.disk_image
    sysmap = args.system_map

    if not os.path.exists(linux_src):
        print(linux_src, "does not exist", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(linux_build):
        print(linux_build, "does not exist", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(hwprof):
        print(hwprof, "does not exist", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(diskimg):
        print(diskimg, "does not exist", file=sys.stderr)
        sys.exit(1)

    if not sysmap and not os.path.exists(sysmap):
        print(sysmap, "does not exist", file=sys.stderr)
        sys.exit(1)

    builtin_objdeplist = os.path.join(args.db_path, "builtin-objs.dep")
    if not os.path.exists(builtin_objdeplist):
        print(builtin_objdeplist, "does not exist", file=sys.stderr)
        sys.exit(1)
    btobj_deps = gen_objdep.load_btobj_deps(args.kernel_build, builtin_objdeplist)

    busreg_lists = [
            os.path.join(args.db_path, "bus-regfuns.db"),
            os.path.join(args.db_path, "class-regfuns.db"),
            ]
    for busreg in busreg_lists:
        if not os.path.exists(busreg):
            print(busreg, "does not exist", file=sys.stderr)
            sys.exit(1)

    busreg_apis = gen_objdep.load_busreg_apis(args.kernel_build, busreg_lists)
    hwdb = os.path.join(args.db_path, "hw.db")
    if not os.path.exists(hwdb):
        print(hwdb, "does not exists", file=sys.stderr)
        sys.exit(1)

    if args.guestmount:
        img_mounted = mount_image(diskimg)
    else:
        img_mounted = diskimg

    _, rm, _, bi_rm, _, _, _, mod_dep, builtin_dep, mod_builtin_dep, noentry, fdep_func, fdep_ko, _, _, _ = \
        analyze_image(img_mounted, busreg_apis, btobj_deps, linux_src, linux_build, hwprof, hwdb, sysmap)

    patch_image(img_mounted, rm, bi_rm, mod_dep, builtin_dep, mod_builtin_dep, noentry, fdep_func, fdep_ko, linux_build, sysmap)

    if args.guestmount:
        unmount_image(img_mounted)

    sys.exit(0)
