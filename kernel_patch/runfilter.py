#!/usr/bin/env python3

import os
import sys
import time
import pickle
import psutil
import subprocess
import hwfilter
import multiprocessing
from argparse import ArgumentParser, Namespace

CURDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURDIR, "..", "dependency"))
import gen_objdep

def parse_arguments(cli_args = None):
    parser = ArgumentParser(description='Run Driver Removal Pass')
    parser.add_argument('-k', '--kernel-path', action='store', required=True,
                        help='kernel source path')
    parser.add_argument('-b', '--kernel-build', action='store', required=True,
                        help='kernel build path')
    parser.add_argument('-P', '--dataset-path', action='store', required=True,
                        help='directory to find datasets target images && HW profiles')
    parser.add_argument('-p', '--db-path', action='store', required=True,
                        help='directory to find dependency dbs')
    parser.add_argument('-o', '--output-path', action='store', required=True,
                        help='output path')
    parser.add_argument('-t', '--test-only', action='store_true',
                        help='test-only flag, so we will NOT patch kernel/images')
    parser.add_argument('-n', '--num-workers', action='store',
                        help='number of worker threads')
    return parser.parse_args(args=cli_args)


def img_umount(chkdir):
    #os.system(f"sudo umount -fl {chkdir}")
    # Known umount issue: https://www.libguestfs.org/guestmount.1.html
    #os.system(f"guestunmount {chkdir}")
    try:
        subprocess.run(['guestunmount', chkdir], check=True)
        print(f"umounting {chkdir}")
        pidfile = os.path.basename(chkdir)+".pid"
        with open(pidfile, 'r') as fd:
            pid = int(fd.read())
        while psutil.pid_exists(pid):
            time.sleep(1)
        os.system(f"rm {pidfile}")
    except subprocess.CalledProcessError:
        return False
    return True
#def img_umount(chkdir):
#    #os.system(f"sudo umount -fl {chkdir}")
#    os.system(f"guestunmount {chkdir}")
#    print(f"umounting {chkdir}")
#    while os.path.exists(os.path.join(chkdir, 'boot')):
#        time.sleep(1)

def worker(outs, busreg_apis, btobj_deps, linux_src, linux_build, dev, db, chkdir, img):
    new_img = os.path.basename(img) + os.path.basename(dev).split('.')[0] + ".test"
    os.system(f"cp '{img}' '{new_img}'")
    tag = os.path.basename(img)
    print(os.path.basename(dev), os.path.basename(img), chkdir)

    if os.path.basename(img) == "suse.raw":
        os.system(f"guestmount -a {new_img} --rw -m /dev/sda2 --pid-file {os.path.basename(chkdir)}.pid {chkdir}")
    else:
        os.system(f"guestmount -a {new_img} --rw -i --pid-file {os.path.basename(chkdir)}.pid {chkdir}")

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
    coremod = set()
    coredep = set()
    fdep_func = set()
    fdep_ko = set()
    allkernfunc = set()

    tup = hwfilter.check_drivers(dev, db, chkdir, busreg_apis, btobj_deps, linux_src, linux_build, tag=os.path.basename(img))
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
    coremod.update(tup[11])
    coredep.update(tup[12])
    fdep_func.update(tup[13])
    fdep_ko.update(tup[14])
    allkernfunc.update(tup[15])
    allbtdrv = tup[16]
    rmbtdrv = tup[17]

    total_size = hwfilter.calc_module_size(chkdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep)

    img_umount(chkdir)
    time.sleep(10)  # Wait unmount
    os.system(f"rm {new_img}")

    outs[(tag, dev)] = (db_match, rm, unk, bi_rm, allmod, bi_match, allbuiltin, mod_dep, builtin_dep, mod_builtin_dep, noentry, coremod, coredep, fdep_func, fdep_ko, allkernfunc, total_size, img, allbtdrv, rmbtdrv)
    print(f"Known mod: {len(db_match)}, All mod: {len(allmod)}, Remove: {len(rm)} + {len(mod_dep)}, Unknown mod: {len(unk)}, Builtin Remove: {len(bi_rm)} + {len(builtin_dep)}, Known Builtin: {len(bi_match)}, All Builtin: {len(allbuiltin)}, Mod dep over Builtin: {len(mod_builtin_dep)}, NoEntry Mod Deps to remove: {len(noentry)}, Core Mod Removed: {len(coremod)}({len(coremod.difference(rm|mod_dep|noentry))}), Core Deps Removed: {len(coredep)}({len(coredep.difference(rm|mod_dep|noentry))})")


if __name__ == '__main__':
    args = parse_arguments()

    if args.test_only:
        testonly = True
    else:
        testonly = False

    if args.num_workers:
        THREADS = int(args.num_workers)
    else:
        THREADS = 1

    hwlist = [
            os.path.join(args.dataset_path, "hwenv/aws-t2-micro.txt"),
            os.path.join(args.dataset_path, "hwenv/azure-v1.txt"),
            os.path.join(args.dataset_path, "hwenv/azure-v2-amd.txt"),
            os.path.join(args.dataset_path, "hwenv/azure-v2-intel.txt"),
            os.path.join(args.dataset_path, "hwenv/gcp-e2-micro.txt"),
            os.path.join(args.dataset_path, "hwenv/qemu-kvm.txt"),
            os.path.join(args.dataset_path, "hwenv/hyperv.txt"),
            ]
    if not testonly:
        hwlist = [
                os.path.join(args.dataset_path, "hwenv/qemu-kvm.txt"),
                ]
    imglist = [
            os.path.join(args.dataset_path, "images/CentOS-Stream-ec2-9-20220829.0.x86_64.raw"),
            os.path.join(args.dataset_path, "images/openSUSE-Leap-15.4.x86_64-1.0.1-GCE-Build2.85.raw"),
            os.path.join(args.dataset_path, "images/debian-11-genericcloud-amd64-20220816-1109.raw"),
            os.path.join(args.dataset_path, "images/debian-11-nocloud-amd64-20220816-1109.raw"),
            os.path.join(args.dataset_path, "images/Fedora-Cloud-Base-GCP-36-20220506.n.0.x86_64.raw"),
            os.path.join(args.dataset_path, "images/ubuntu.raw"),
            os.path.join(args.dataset_path, "images/fedora-server.raw"),
            os.path.join(args.dataset_path, "images/fedora-workstation.raw"),
            os.path.join(args.dataset_path, "images/suse.raw"),
            os.path.join(args.dataset_path, "images/ubuntu-ec2-22.04.raw"),
            os.path.join(args.dataset_path, "images/ubuntu-azure-22.04.raw"),
            os.path.join(args.dataset_path, "images/ubuntu-gcp-22.04.raw"),
            ]

    total_tab = dict()
    drvrm_tab = dict()
    btinrm_tab = dict()
    noentrm_tab = dict()
    corerm_tab = dict()
    final_rm = dict()
    final_fdep_kern = dict()
    final_fdep_mod = dict()
    total_size = dict()
    total_func = dict()
    total_initrdrm = dict()

    #linux_build="/home/hu/workspace/hu/linux/build_llvm"
    #linux_src="/home/hu/workspace/hu/linux"
    #builtin_objdeplist = "/home/hu/workspace/hu/uForkLift/coredev_v2/5.19.17/builtin-z3-allmodconfig.txt"
    builtin_objdeplist = os.path.join(args.db_path, "builtin-objs.dep")
    btobj_deps = gen_objdep.load_btobj_deps(args.kernel_build, builtin_objdeplist)

    #BUS_REG_APIs = "../coredev_v2/5.19.17/bus-regfuns.txt"
    busreg_lists = [
            os.path.join(args.db_path, "bus-regfuns.db"),
            os.path.join(args.db_path, "class-regfuns.db"),
            ]
    busreg_apis = gen_objdep.load_busreg_apis(busreg_lists)

    for i in range(THREADS):
        os.system(f"mkdir -p {os.path.join(args.output_path, 'bigroot', str(i))}")

    hwdb = os.path.join(args.db_path, "hw.db")
    worklist = []
    for hw in hwlist:
        for img in imglist:
            worklist.append((hw, hwdb, os.path.join(args.output_path, "bigroot"), img))

    #for dev, db, chkdir in azure_v2_worklist:
    #    _,_,_,modlist = hwfilter.load_db(dev,db)
    #    print(modlist)
    #exit(0)

    #for dev, db, chkdir in azure_v2_worklist:
    #    hwfilter.repack_kernel(chkdir)

    manager = multiprocessing.Manager()
    results = manager.dict()
    pool = [None] * THREADS
    initial = True
    for dev, db, chkdir, img in worklist:
        if initial: # Initialize caches
            chkdir = os.path.join(chkdir, str(0))
            p = multiprocessing.Process(target=worker, args=(results, \
                    busreg_apis, btobj_deps, args.kernel_path, args.kernel_build, \
                    dev, db, chkdir, img))
            p.start()
            p.join()
            initial = False
            continue
        for i in range(THREADS):
            if not pool[i] or not pool[i].is_alive():
                chkdir = os.path.join(chkdir, str(i))
                if pool[i]:
                    pool[i].join()
                pool[i] = multiprocessing.Process(target=worker, args=(results, \
                        busreg_apis, btobj_deps, args.kernel_path, args.kernel_build, \
                        dev, db, chkdir, img))
                pool[i].start()
                break
        while False not in [p!=None and p.is_alive() for p in pool]:
            time.sleep(10)

        #print([x for x in rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep if 'kvm' in x])
        #print("scsi_transport_iscsi" in coremod)
        #print("ib_core" in coremod)
    for i in range(THREADS):
        if pool[i]:
            pool[i].join()


    dres = dict()
    for tag, hw in results:
        dres[(tag, hw)] = results[(tag, hw)]

    # Patch
    for tag, hw in dres:
        tup = dres[(tag, hw)]
        db_match = tup[0]
        rm = tup[1]
        unk = tup[2]
        bi_rm = tup[3]
        allmod = tup[4]
        bi_match = tup[5]
        allbuiltin = tup[6]
        mod_dep = tup[7]
        builtin_dep = tup[8]
        mod_builtin_dep = tup[9]
        noentry = tup[10]
        coremod = tup[11]
        coredep = tup[12]
        fdep_func = tup[13]
        fdep_ko = tup[14]
        allkernfunc = tup[15]
        totalsz = tup[16]
        img = tup[17]
        allbtdrv = tup[18]
        rmbtdrv = tup[19]

        tag = os.path.basename(img)
        print(os.path.basename(dev), os.path.basename(img))
        if not testonly:
            chkdir = os.path.abspath(os.path.join(args.output_path, "bigroot", "0"))
            workdir = os.path.abspath(os.path.join(args.output_path, "repack"))
            if not os.path.exists(workdir):
                os.makedirs(workdir, exist_ok=True)
            ctl_img = os.path.basename(img)+".ctl"
            patch_img = os.path.basename(img) + os.path.basename(dev).split('.')[0] + ".patched"
            os.system(f"cp '{img}' '{ctl_img}'")
            os.system(f"cp '{img}' '{patch_img}'")

            # Prepare Control Image
            #if os.path.basename(img) == "suse.raw":
            #    os.system(f"guestmount -a {ctl_img} --rw -m /dev/sda2 --pid-file {os.path.basename(chkdir)}.pid {chkdir}")
            #else:
            #    os.system(f"guestmount -a {ctl_img} --rw -i --pid-file {os.path.basename(chkdir)}.pid {chkdir}")

            #hwfilter.replace_init(chkdir)
            #img_umount(chkdir)

            # Prepare Testing Image
            if os.path.basename(img) == "suse.raw":
                os.system(f"guestmount -a {patch_img} --rw -m /dev/sda2 --pid-file {os.path.basename(chkdir)}.pid {chkdir}")
            else:
                os.system(f"guestmount -a {patch_img} --rw -i --pid-file {os.path.basename(chkdir)}.pid {chkdir}")

            def patchcb(vmlinux):
                #patchlist = [x for x in bi_rm|builtin_dep if 'dm_' not in x]
                return hwfilter.patch_builtin(vmlinux, bi_rm|builtin_dep|fdep_func, hwfilter.get_target_info(chkdir)[1])

            newkern = hwfilter.repack_kernel(chkdir, workdir, patchcb)

            #hwfilter.replace_init(chkdir)
            hwfilter.replace_kernel(chkdir, newkern)
            hwfilter.remove_module(chkdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep)
            hwfilter.patch_module(chkdir, fdep_ko)
            if os.path.basename(img) in [
                    "openSUSE-Leap-15.4.x86_64-1.0.1-GCE-Build2.85.raw",
                    "suse.raw",
                    ]:
                #print(mod_builtin_dep)
                #hwfilter.patch_initrd(chkdir, set(), ["scsi", "ata", "phy"], opensuse_fstab_patch=True)
                initrdstat = (0, 0)
                initrdstat = hwfilter.patch_initrd(chkdir, workdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep, ["scsi_mod", "ata", "sd_mod"])
            else:
                initrdstat = hwfilter.patch_initrd(chkdir, workdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep, ["scsi_mod", "ata", "sd_mod"])
            hwfilter.remove_firmware(chkdir)

            #hwfilter.check_rop_gadgets(tag)

            img_umount(chkdir)
        else:
            initrdstat = (0, 0)

        #print(f"Known mod: {len(db_match)}, All mod: {len(allmod)}, Remove: {len(rm)} + {len(mod_dep)}, Unknown mod: {len(unk)}, Builtin Remove: {len(bi_rm)} + {len(builtin_dep)}, Known Builtin: {len(bi_match)}, All Builtin: {len(allbuiltin)}, Mod dep over Builtin: {len(mod_builtin_dep)}, NoEntry Mod Deps to remove: {len(noentry)}, Core Mod Removed: {len(coremod)}({len(coremod.difference(rm|mod_dep|noentry))}), Core Deps Removed: {len(coredep)}({len(coredep.difference(rm|mod_dep|noentry))})")
        #print(allmod.difference(rm))
        #print(mod_builtin_dep)
        #print(mod_dep)
        #print(bi_match.difference(bi_rm))
        #print(db_match)
        #print(rm)
        #print(noentry)

        #print(coremod.difference(rm|mod_dep|noentry))
        #print(len(allbuiltin.difference(bi_match|builtin_dep)))
        #print("\n".join(allbuiltin.difference(bi_match|builtin_dep)))
        #print(len(fdep_func), len(fdep_ko), len(set([x[1] for x in fdep_ko])))

        total_tab[tag] = (len(allmod), len(db_match), len(allbuiltin), len(bi_match))
        if tag not in drvrm_tab:
            drvrm_tab[tag] = {}
        drvrm_tab[tag][hw] = (len(rm), len(mod_dep))
        if tag not in btinrm_tab:
            btinrm_tab[tag] = {}
        btinrm_tab[tag][hw] = (len(bi_rm), len(builtin_dep), len(mod_builtin_dep))
        if tag not in noentrm_tab:
            noentrm_tab[tag] = {}
        noentrm_tab[tag][hw] = len(noentry)
        if tag not in corerm_tab:
            corerm_tab[tag] = {}
        corerm_tab[tag][hw] = (len(coremod), len(coredep))
        if tag not in final_rm:
            final_rm[tag] = {}
        final_rm[tag][hw] = len(rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep)
        if tag not in final_fdep_kern:
            final_fdep_kern[tag] = {}
        final_fdep_kern[tag][hw] = len(fdep_func)
        if tag not in final_fdep_mod:
            final_fdep_mod[tag] = {}
        final_fdep_mod[tag][hw] = (len(set([x[1] for x in fdep_ko])), len(fdep_ko))
        if tag not in total_size:
            total_size[tag] = {}
        total_size[tag][hw] = totalsz
        if tag not in total_func:
            total_func[tag] = {}
        total_func[tag][hw] = len(allkernfunc)
        if tag not in total_initrdrm:
            total_initrdrm[tag] = {}
        total_initrdrm[tag][hw] = initrdstat


    print("Total :")
    for tag in total_tab:
        t = total_tab[tag]
        print(f"{tag} & {t[0]} & {t[1]} & {t[2]} & {t[3]} \\\\")
    print()
    print("Driver Removal:")
    for tag in drvrm_tab:
        s = f"{tag} "
        for hw in hwlist:
            t = drvrm_tab[tag][hw]
            s += f"& {t[0]} + {t[1]} "
        s += "\\\\"
        print(s)
    print()
    print("Built-in Removal:")
    for tag in btinrm_tab:
        s = f"{tag} "
        for hw in hwlist:
            t = btinrm_tab[tag][hw]
            s += f"& {t[0]} + {t[1]} ({t[2]}) "
        s += "\\\\"
        print(s)
    print()
    print("NoEntry Removal:")
    for tag in noentrm_tab:
        s = f"{tag} "
        for hw in hwlist:
            t = noentrm_tab[tag][hw]
            s += f"& {t} "
        s += "\\\\"
        print(s)
    print()
    print("Core Removal (Deprecated):")
    for tag in corerm_tab:
        s = f"{tag} "
        for hw in hwlist:
            t = corerm_tab[tag][hw]
            s += f"& {t[0]} + {t[1]} "
        s += "\\\\"
        print(s)
    print()
    print("Function Deps kernel image patched:")
    for tag in final_fdep_kern:
        s = f"{tag} "
        for hw in hwlist:
            t = final_fdep_kern[tag][hw]
            s += f"& {t}/{total_func[tag][hw]} "
        s += "\\\\"
        print(s)
    print()
    print("Function Deps modules patched:")
    for tag in final_fdep_mod:
        s = f"{tag} "
        for hw in hwlist:
            t = final_fdep_mod[tag][hw]
            s += f"& {t[0]} + {t[1]} "
        s += "\\\\"
        print(s)

    print("Final modules removed:")
    for tag in final_rm:
        s = f"{tag} "
        for hw in hwlist:
            s += f"& {final_rm[tag][hw]}/{float(total_size[tag][hw])/1024/1024:.3f} "
        s += "\\\\"
        print(s)

    print("Initrd rm count")
    for tag in final_rm:
        s = f"{tag} "
        for hw in hwlist:
            s += f"& {total_initrdrm[tag][hw][0]} & {total_initrdrm[tag][hw][1]} "
        s += "\\\\"
        print(s)

    exit(0)

