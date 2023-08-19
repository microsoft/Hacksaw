#!/usr/bin/env python3

import os
import hwfilter

testonly = True
testonly = False

hwlist = [
        "../hwenv/aws-t2-micro.txt",
        "../hwenv/azure-v1.txt",
        "../hwenv/azure-v2-amd.txt",
        "../hwenv/azure-v2-intel.txt",
        "../hwenv/gcp-e2-micro.txt",
        "../hwenv/qemu-kvm.txt",
        "../hwenv/hyperv.txt",
        ]
#hwlist = [
#        "../hwenv/aws-t2-micro.txt",
#        ]
if not testonly:
    hwlist = [
            "../hwenv/qemu-kvm.txt",
            ]
imglist = [
        "../../dataset/centos/CentOS-Stream-ec2-9-20220829.0.x86_64.raw",
        #"../../dataset/centos/CentOS-Stream-GenericCloud-9-20220829.0.x86_64.qcow2",
        #"../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-Azure-Build2.87.vhdfixed",
        #"../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-EC2-Build2.86.raw",
        "../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-GCE-Build2.85.raw",
        #"../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-NoCloud-Build2.85.qcow2",
        #"../../dataset/debian/debian-11-azure-amd64-20220816-1109.raw",
        #"../../dataset/debian/debian-11-ec2-amd64-20220816-1109.raw",
        #"../../dataset/debian/debian-11-generic-amd64-20220816-1109.raw",
        "../../dataset/debian/debian-11-genericcloud-amd64-20220816-1109.raw",
        "../../dataset/debian/debian-11-nocloud-amd64-20220816-1109.raw",
        "../../dataset/ubuntu/ubuntu-ec2-22.04.raw",
        #"../../dataset/ubuntu/ubuntu-azure-22.04.raw",
        "../../dataset/ubuntu/ubuntu-gcp-22.04.raw",
        "../../dataset/opensuse/opensuse-bare.raw",
        "/data/isos/ubuntu.raw",
        "../../dataset/opensuse/opensuse-server-cd.raw",
        "/data/isos/fedora-server.raw",
        "/data/isos/fedora-workstation.raw",
        "../../dataset/fedora/Fedora-Cloud-Base-36-1.5.x86_64.raw",
        "../../dataset/fedora/Fedora-Cloud-Base-GCP-36-20220506.n.0.x86_64.raw",
        ]
imglist = [
        "../../dataset/centos/CentOS-Stream-ec2-9-20220829.0.x86_64.raw",
        #"../../dataset/centos/CentOS-Stream-GenericCloud-9-20220829.0.x86_64.qcow2",
        #"../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-Azure-Build2.87.vhdfixed",
        #"../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-EC2-Build2.86.raw",
        "../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-GCE-Build2.85.raw",
        #"../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-NoCloud-Build2.85.qcow2",
        #"../../dataset/debian/debian-11-azure-amd64-20220816-1109.raw",
        #"../../dataset/debian/debian-11-ec2-amd64-20220816-1109.raw",
        #"../../dataset/debian/debian-11-generic-amd64-20220816-1109.raw",
        "../../dataset/debian/debian-11-genericcloud-amd64-20220816-1109.raw",
        "../../dataset/debian/debian-11-nocloud-amd64-20220816-1109.raw",
        "../../dataset/fedora/Fedora-Cloud-Base-36-1.5.x86_64.raw",
        "../../dataset/fedora/Fedora-Cloud-Base-GCP-36-20220506.n.0.x86_64.raw",
        "/data/isos/ubuntu.raw",
        "/data/isos/fedora-server.raw",
        "/data/isos/fedora-workstation.raw",
        "/data/isos/suse.raw", #"../../dataset/opensuse/opensuse-server-cd.raw",
        "../../dataset/ubuntu/ubuntu-ec2-22.04.raw",
        "../../dataset/ubuntu/ubuntu-azure-22.04.raw",
        "../../dataset/ubuntu/ubuntu-gcp-22.04.raw",

        # NoBoot
        "../../dataset/opensuse/opensuse-bare.raw",
        ]
imglist = [
        "/data/isos/ubuntu.raw",
        ]

total_tab = dict()
drvrm_tab = dict()
btinrm_tab = dict()
noentrm_tab = dict()
corerm_tab = dict()
final_rm = dict()
total_size = dict()

BUS_REG_APIs = "../coredev_v2/5.19.17/bus-regfuns.txt"

busreg_apis = set()
with open(BUS_REG_APIs, 'r') as fd:
    data = fd.read().strip()
    for line in data.split('\n'):
        line = line.strip()
        if not line:
            continue
        _, api = line.split()
        busreg_apis.add(api)

worklist = []
for hw in hwlist:
    for img in imglist:
        worklist.append((hw, "../gen_database/platform.db", "../../bigroot", img))
#worklist = [
#        #("../hwenv/hyperv.txt", "../gen_database/platform.db", "../../bigroot", "../../testubuntuserver.vhdx_bak"),
#        ("../hwenv/hyperv.txt", "../gen_database/platform.db", "../../bigroot", "../../dataset/debian/debian-11-nocloud-amd64-20220816-1109.raw"),
#        ]

#for dev, db, chkdir in azure_v2_worklist:
#    _,_,_,modlist = hwfilter.load_db(dev,db)
#    print(modlist)
#exit(0)

#for dev, db, chkdir in azure_v2_worklist:
#    hwfilter.repack_kernel(chkdir)

for dev, db, chkdir, img in worklist:
    tag = os.path.basename(img)
    print(os.path.basename(dev), os.path.basename(img))
    if not testonly:
        ctl_img = os.path.basename(img)+".ctl"
        patch_img = os.path.basename(img)+".patched"
        os.system(f"cp '{img}' '{ctl_img}'")
        os.system(f"cp '{img}' '{patch_img}'")
    else:
        patch_img = img

    if not testonly:
        if img == "/data/isos/suse.raw":
            os.system(f"guestmount -a {ctl_img} --rw -m /dev/sda2 {chkdir}")
        else:
            os.system(f"guestmount -a {ctl_img} --rw -i {chkdir}")
        hwfilter.replace_init(chkdir)
        os.system(f"umount {chkdir}")

    if img == "/data/isos/suse.raw":
        os.system(f"guestmount -a {patch_img} --rw -m /dev/sda2 {chkdir}")
    else:
        os.system(f"guestmount -a {patch_img} --rw -i {chkdir}")
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

    tup = hwfilter.check_drivers(dev, db, chkdir, busreg_apis, tag=os.path.basename(img))
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

    print([x for x in rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep if 'kvm' in x])
    print("scsi_transport_iscsi" in coremod)
    print("ib_core" in coremod)

    if tag not in total_size:
        total_size[tag] = []
    total_size[tag].append(hwfilter.calc_module_size(chkdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep))

    if not testonly:
        def patchcb(vmlinux):
            #patchlist = [x for x in bi_rm|builtin_dep if 'dm_' not in x]
            return hwfilter.patch_builtin(vmlinux, bi_rm|builtin_dep|fdep_func, hwfilter.get_target_info(chkdir)[1])

        newkern = hwfilter.repack_kernel(chkdir, patchcb)

        hwfilter.replace_init(chkdir)
        hwfilter.replace_kernel(chkdir, newkern)
        hwfilter.remove_module(chkdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep)
        hwfilter.patch_module(chkdir, fdep_ko)
        if img == "../../dataset/opensuse/openSUSE-Leap-15.4.x86_64-1.0.1-GCE-Build2.85.raw":
            hwfilter.patch_initrd(chkdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep, "iscsi")
        else:
            hwfilter.patch_initrd(chkdir, rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep)
        hwfilter.remove_firmware(chkdir)

    os.system(f"umount {chkdir}")

    print(f"Known mod: {len(db_match)}, All mod: {len(allmod)}, Remove: {len(rm)} + {len(mod_dep)}, Unknown mod: {len(unk)}, Builtin Remove: {len(bi_rm)} + {len(builtin_dep)}, Known Builtin: {len(bi_match)}, All Builtin: {len(allbuiltin)}, Mod dep over Builtin: {len(mod_builtin_dep)}, NoEntry Mod Deps to remove: {len(noentry)}, Core Mod Removed: {len(coremod)}({len(coremod.difference(rm|mod_dep|noentry))}), Core Deps Removed: {len(coredep)}({len(coredep.difference(rm|mod_dep|noentry))})")
    #print(allmod.difference(rm))
    #print(mod_builtin_dep)
    #print(mod_dep)
    #print(bi_match.difference(bi_rm))
    #print(db_match)
    #print(rm)
    #print(noentry)

    #print(coremod.difference(rm|mod_dep|noentry))
    print(len(allbuiltin.difference(bi_match|builtin_dep)))
    #print("\n".join(allbuiltin.difference(bi_match|builtin_dep)))
    print(len(fdep_func), len(fdep_ko))

    total_tab[tag] = (len(allmod), len(db_match), len(allbuiltin), len(bi_match))
    if tag not in drvrm_tab:
        drvrm_tab[tag] = []
    drvrm_tab[tag].append((len(rm), len(mod_dep)))
    if tag not in btinrm_tab:
        btinrm_tab[tag] = []
    btinrm_tab[tag].append((len(bi_rm), len(builtin_dep), len(mod_builtin_dep)))
    if tag not in noentrm_tab:
        noentrm_tab[tag] = []
    noentrm_tab[tag].append(len(noentry))
    if tag not in corerm_tab:
        corerm_tab[tag] = []
    corerm_tab[tag].append((len(coremod), len(coredep)))
    if tag not in final_rm:
        final_rm[tag] = []
    final_rm[tag].append(len(rm|mod_dep|mod_builtin_dep|noentry|coremod|coredep))


print("Total :")
for tag in total_tab:
    t = total_tab[tag]
    print(f"{tag} & {t[0]} & {t[1]} & {t[2]} & {t[3]} \\\\")
print()
print("Driver Removal:")
for tag in drvrm_tab:
    s = f"{tag} "
    for t in drvrm_tab[tag]:
        s += f"& {t[0]} + {t[1]} "
    s += "\\\\"
    print(s)
print()
print("Built-in Removal:")
for tag in btinrm_tab:
    s = f"{tag} "
    for t in btinrm_tab[tag]:
        s += f"& {t[0]} + {t[1]} ({t[2]}) "
    s += "\\\\"
    print(s)
print()
print("NoEntry Removal:")
for tag in noentrm_tab:
    s = f"{tag} "
    for t in noentrm_tab[tag]:
        s += f"& {t} "
    s += "\\\\"
    print(s)
print()
print("Core Removal:")
for tag in corerm_tab:
    s = f"{tag} "
    for t in corerm_tab[tag]:
        s += f"& {t[0]} + {t[1]} "
    s += "\\\\"
    print(s)

print("Final modules removed:")
for tag in final_rm:
    s = f"{tag} "
    for i in range(len(final_rm[tag])):
        s += f"& {final_rm[tag][i]}/{float(total_size[tag][i])/1024/1024:.3f} "
    s += "\\\\"
    print(s)

exit(0)

