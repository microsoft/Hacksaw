#!/usr/bin/env python3

import os
import sys
import time
import shlex
import subprocess
#import multiprocessing


linux_build = sys.argv[1]
cc = 'clang'
nproc = len(os.sched_getaffinity(0))

cmd_files = []
for root,_,files in os.walk(linux_build):
    for f in files:
        if f.startswith('.') and f.endswith('.cmd'):
            cmd_files.append(os.path.join(root, f))

build_cmd = dict()
for f in cmd_files:
    with open(f, 'r') as fd:
        data = fd.read()
        for line in data.split('\n'):
            if line.startswith('cmd_') or line.startswith('savedcmd'):
                cmd = line[line.find(' := ')+4:]
                if ';' in cmd:
                    cmd = cmd[:cmd.find(';')]
                if os.path.basename(cmd.split()[0]) == cc:
                    build_cmd[f] = cmd.strip()
                break

pool = [None] * nproc
for f in build_cmd:
    cmd = shlex.split(build_cmd[f])
    #if '-c' not in cmd:
    #    continue
    cmd += ['-emit-llvm', '-o', os.path.join(os.path.dirname(f[len(linux_build)+1:]), os.path.basename(f)[1:-4]+'.bc')]
    print(cmd)
    if None in pool:
        pool[pool.index(None)] = subprocess.Popen(cmd, cwd=linux_build)
    if None not in pool:
        while False not in map(lambda x: x.poll()==None, pool):
            time.sleep(1)
        for i in range(len(pool)):
            if pool[i].poll() != None:
                pool[i] = None

map(lambda x: x.wait(), pool)
