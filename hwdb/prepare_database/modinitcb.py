#!/usr/bin/env python3

import os
import re
import sys
#import shlex
import subprocess

curdir = os.path.dirname(os.path.realpath(__file__))

# For new devices, update ~/modinitcb_macro.list and run ~/modinitcb.sh
# grep -wrF "module_hid_driver" .|grep ":module_hid_driver(" >> ~/modinit.log
patlist = os.path.join(curdir, "modinitcb_macro.list")
greplog = os.path.join(curdir, "modinit.log")
noentrylist = os.path.join(curdir, "noentry.list")
log = os.path.join(curdir, "modinit.db")

#output = subprocess.check_output(shlex.join([ \
#        'grep', '-wrF', '"module_init"', \
#        os.path.dirname(linux_build), \
#        '|', 'grep', '":module_init("', \
#        '|', 'grep', '"#"']), shell=True)
#p1 = subprocess.Popen([ \
#        'grep', '-wrF', 'module_init', \
#        os.path.dirname(linux_build), \
#        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#p2 = subprocess.Popen(['grep', ':module_init('],
#        stdin=p1.stdout, stdout=subprocess.PIPE)
#p3 = subprocess.Popen(['grep', '-v', '#'],
#        stdin=p1.stdout, stdout=subprocess.PIPE)
#p3.wait()

#data = p3.stdout.read()

def resolve_from_mk(f, linux_src, toplevel=True):
    if f.startswith("include/"):
        return ({}, {})
    mk = os.path.join(linux_src, os.path.dirname(f), "Makefile")
    while not os.path.exists(mk):
        mk = os.path.join(os.path.dirname(mk), "Kbuild")
        if os.path.exists(mk):
            break
        pdir = os.path.dirname(os.path.dirname(mk))
        mk = os.path.join(pdir, "Makefile")
    # Possible third-party driver
    if os.path.dirname(mk) == os.path.normpath(linux_src):
        return ({}, {})
    #print(f, mk)
    #assert (os.path.dirname(mk) != os.path.normpath(linux_src))
    assert (os.path.exists(mk))
    rules = []
    with open(mk, 'r') as fd:
        data = fd.read().strip().split('\n')
        combflag = False
        for line in data:
            line = line.strip()
            #print("Debug line: ", line)
            if combflag:
                #print("combining", line)
                rules[-1] += ' '
                if line.endswith('\\'):
                    rules[-1] += line[:-1]
                else:
                    rules[-1] += line
                    combflag = False
            elif re.match(f'^{os.path.basename(f).split(".")[0]+".o"}\s*[:+=]', line) \
                or re.match(f'^{os.path.basename(f).split(".")[0]}-objs\s*[:+=]', line) \
                or re.match(f'^{os.path.basename(f).split(".")[0]}-y\s*[:+=]', line) \
                or re.match(f'^{os.path.basename(f).split(".")[0]}-m\s*[:+=]', line) \
                or re.match(f'^{os.path.basename(f).split(".")[0]}-\$\(', line) \
                or re.match(f'^\$\(obj\)/{os.path.basename(f).split(".")[0]}\.o\s*:', line) \
                or (toplevel and re.match(f'^obj-\$\(CONFIG_.*\)\s*\+=\s*{os.path.basename(f).split(".")[0]}', line)):
                #print("macro start", line)
                if line.endswith('\\'):
                    rules.append(line[:-1])
                    combflag = True
                else:
                    rules.append(line)
    srcfiles = set()
    objfiles = set()
    for rule in set(rules):
        for src in rule.strip().split()[1:]:
            src = src.strip()
            while src and src[0] in [':', '+', '=']:
                src = src[1:]
            if not src:
                continue

            if "$(srctree)" in src:
                src = re.sub(r"\$\(srctree\)", linux_src, src)
            else:
                src = os.path.join(os.path.dirname(mk), src)
            src = os.path.relpath(src, linux_src)
            if src.endswith('.c'):
                srcfiles.add(src)
            elif src.endswith('.o'):
                # Avoid Recursion: drivers/gpu/drm/i915/gvt/Makefile
                if os.path.basename(src).split(".")[0] \
                        != os.path.basename(f).split(".")[0]:
                    tmpsrc, tmpobj = resolve_from_mk(src, linux_src, False)
                    srcfiles.update(tmpsrc)
                    objfiles.update(tmpobj)
                objfiles.add(src)
    return srcfiles, objfiles

def get_pats(patlist):
    modpats = []
    with open(patlist, 'r') as fd:
        for line in fd.read().strip().split('\n'):
            modpats.append(
                re.compile(r"{}\s*\((.*)\)".format(line.strip())))
    #initpat = re.compile(r"module_init\((.*)\)")
    #usbpat = re.compile(r"module_usb_driver\((.*)\)")
    #hidpat = re.compile(r"module_hid_driver\((.*)\)")
    #virtiopat = re.compile(r"module_virtio_driver\((.*)\)")
    return modpats

def get_initmap(greplog, linux_src, modpats):
    modinit_map = dict()
    with open(greplog, 'r') as fd:
        data = fd.read().strip().split('\n')
        for line in data:
            p, s = line.strip().split(":")
            s = s.strip()
            if ')' not in s:
                with open(os.path.join(linux_src, p), 'r') as srcfd:
                    data = srcfd.read()
                    sstart = data.find(s)
                    s = data[sstart: data.find(')', sstart)+1]
                    s = ''.join(s.split('\n'))
            cb = ''
            for pat in modpats:
                if pat.match(s):
                    cb = pat.match(s).group(1)
                    break
            if not cb:
                continue
            alias = 'x'
            if s.startswith("IRQCHIP_DECLARE") or \
                    s.startswith("CLK_OF_DECLARE") or \
                    s.startswith("TIMER_OF_DECLARE") or \
                    s.startswith("module_vfio_reset_handler") \
                    :
                #print(s, cb)
                alias = ''
                if '"' not in cb:
                    tup = cb.split(',')
                    with open(os.path.join(linux_src, p), 'r') as srcfd:
                        for line in srcfd.read().split('\n'):
                            line = line.strip()
                            if line.startswith("#define") and tup[-2].strip() in line:
                                alias = line.split()[2].strip()
                    if not alias:
                        tmpout = subprocess.check_output(["grep", "-wrF", tup[-2].strip(), os.path.join(linux_src, 'include')])
                        for line in tmpout.decode('latin-1').split('\n'):
                            line = line[line.find(':')+1:]
                            if line.startswith("#define") and tup[-2].strip() in line:
                                alias = line.split()[2].strip()
                    cb = tup[-1].strip()
                else:
                    tup = cb.split('"')
                    assert (len(tup) == 3)
                    alias = tup[1]
                    cb = tup[2].split(',')[1].strip()
                assert (alias)
                alias = "of:N*T*C*"+alias
            elif ',' in cb:
                cb = cb.split(',')[0].strip()
            #if initpat.match(s):
            #    cb = initpat.match(s).group(1)
            #elif usbpat.match(s):
            #    cb  = usbpat.match(s).group(1)
            #elif virtiopat.match(s):
            #    cb  = virtiopat.match(s).group(1)
            #elif hidpat.match(s):
            #    cb  = hidpat.match(s).group(1)
            if os.path.normpath(p) not in modinit_map:
                modinit_map[os.path.normpath(p)] = set()
            modinit_map[os.path.normpath(p)].add((cb, alias))
            #print(os.path.normpath(p), cb)
    return modinit_map

# find link info
def get_bcmap(modinit_map, linux_src):
    bclist = set()
    foundfile = set()
    modcb = dict()
    noentry = set()
    nobc = set()
    linux_build = os.path.join(linux_src, "build_llvm")
    for root,_,files in os.walk(linux_build):
        for f in files:
            if f.endswith('.mod'):
                #continue
                m = os.path.join(root, f[:-4]+".ko")
                assert (os.path.exists(m))
                output = subprocess.check_output([os.path.join(curdir, "..", "..", "utils", "get-mod-init.sh"), m])
                mod,cb = output.decode('latin-1').strip().split()
                print(m)
                if cb != "NOINIT":
                    tag = os.path.join(root, f+'.bcmerged')
                    if tag not in modcb:
                        modcb[tag] = set()
                    modcb[tag].add((cb, mod+'.o', 'x'))
                    if not os.path.exists(os.path.join(root, f+".bcmerged")):
                        nobc.add(f)
                    else:
                        bclist.add(os.path.join(root, f+".bcmerged"))
                else:
                    entryfound = False
                    #print(os.path.join(root, f))
                    with open(os.path.join(root, f), 'r') as fd:
                        for obj in fd.read().strip().split('\n'):
                            key = os.path.normpath(obj[:-2]+'.c')
                            #print(key)
                            if key not in modinit_map:
                                continue
                            foundfile.add(key)
                            entryfound = True
                            #tag = f[:-4]
                            tag = os.path.join(root, f+'.bcmerged')
                            print(tag)
                            if tag not in modcb:
                                modcb[tag] = set()
                            for cb, alias in modinit_map[key]:
                                modcb[tag].add((cb, mod, alias))
                                if not os.path.exists(os.path.join(root, f+".bcmerged")):
                                    nobc.add(f)
                                else:
                                    bclist.add(os.path.join(root, f+".bcmerged"))
                            #break
                    if not entryfound:
                        noentry.add(os.path.join(root, f))
            elif f == ".built-in.a.cmd":
                #continue
                wq = [f]
                while wq:
                    f = wq.pop(0)
                    print(os.path.join(root, f))
                    with open(os.path.join(root, f), 'r') as fd:
                        data = fd.read()
                        tag = data.split(':=')[0].strip()[4:]
                        cmd = data.split(';')[1].strip()
                        if cmd.startswith("echo"):
                            objs = cmd.split('|')[0].strip().split()[1:]
                        elif cmd.startswith("printf"):
                            objs = cmd.split('|')[0].strip().split()[3:]
                        else:
                            continue
                        #cfiles = [os.path.join(os.path.relpath(root, linux_build), obj) for obj in objs]
                        for obj in objs:
                            if os.path.basename(obj).startswith("built-in"):
                                btin = os.path.join(
                                    os.path.dirname(f),
                                    os.path.dirname(obj),
                                    ".built-in.a.cmd")
                                wq.append(btin)
                                continue
                            assert (obj[-2] == ".")
                            key = os.path.normpath(
                                os.path.join(
                                    os.path.relpath(root, linux_build),
                                    os.path.dirname(f),
                                    obj[:-2]+'.c'))
                            print(os.path.join(linux_src, key))
                            # Skip assembly
                            if os.path.exists(os.path.join(linux_src, key[:-2]+'.S')):
                                continue
                            # Skip generated source
                            if os.path.exists(os.path.join(linux_build, key)):
                                continue
                            # Skip dtb
                            if obj.endswith(".dtb.o"):
                                continue
                            keys = [key]
                            # Try parse Makefile
                            if not os.path.exists(os.path.join(linux_src, key)):
                                keys,ofs = resolve_from_mk(key, linux_src)
                                #assert (not ofs)
                            for key in keys:
                                assert (os.path.exists(os.path.join(linux_src, key)))
                                if key not in modinit_map:
                                    continue
                                foundfile.add(key)
                                #tag = os.path.join(os.path.relpath(root, linux_build), f)
                                tag = os.path.join(root, f+'.bcmerged')
                                #tag = os.path.join(linux_build, key[:-2]+'.o.bc')
                                if tag not in modcb:
                                    modcb[tag] = set()
                                for cb, alias in modinit_map[key]:
                                    modcb[tag].add((cb, key, alias))
                                    print(os.path.join(linux_build, key))
                                    if (not os.path.exists(os.path.join(linux_build, key[:-2]+'.o.bc'))):
                                        nobc.add(key)
                                    else:
                                        bclist.add(os.path.join(linux_build, key[:-2]+'.o.bc'))
                            #break
            else:
                continue
    #print(noentry)
    #print(nobc)
    return (modcb, bclist, foundfile, noentry, nobc)

if __name__ == '__main__':
    linux_src = os.path.abspath(sys.argv[1])
    modinit_map = get_initmap(greplog, linux_src, get_pats(patlist))
    modcb,_,foundfile,noentry,_ = get_bcmap(modinit_map, linux_src)
    with open(noentrylist, 'w') as fd:
        for tsk in noentry:
            assert (tsk.endswith(".mod"))
            fd.write(tsk[:-4]+".ko"+'\n')
    #exit(0)

    for f in modinit_map:
        if f not in foundfile:
            print(f)
            pass
    print(len(set(modinit_map.keys()).difference(foundfile)))
    with open(log, 'w') as fd:
        for key in modcb:
            for t in modcb[key]:
                modname = os.path.basename(t[1])
                if modname[-2] == '.':
                    modname = modname[:-2]
                fd.write(key+":"+t[0]+","+modname+","+t[2]+"\n")
