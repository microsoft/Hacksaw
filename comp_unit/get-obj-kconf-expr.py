#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import multiprocess as mp
from subprocess import PIPE, Popen
from argparse import ArgumentParser, Namespace
from typing import Dict, List

target_dirs=["arch/x86", "block", "certs", "drivers", "fs", "init", "io_uring", "ipc", "kernel", "lib", "mm", "net", "security", "sound", "usr", "virt"]
# ignore directories like arch/alpha/, Documentation/, include/, LICENSES/, ...

kernel_path = ""
nworkers = 1

def parse_arguments(cli_args: List[str] = None) -> Namespace:
    parser = ArgumentParser(description='Get minimal kernel configuration expressions for each object file')
    parser.add_argument('--kernel-path', action='store', required=True,
                        help='kernel source path')
    parser.add_argument('--num-workers', action='store',
                        help='the number of worker threads')
    return parser.parse_args(args=cli_args)

def load_configs(args: Namespace) -> Dict:
    try:
        global kernel_path
        kernel_path=os.path.realpath(args.kernel_path)
        if not os.path.exists(kernel_path):
            print(kernel_path, "does not exist", file=sys.stderr)
            return False

        global nworkers
        if args.num_workers != None:
            nworkers = int(args.num_workers)

    except Exception as err:
        print(err)
        if err == "Really Bad":
            raise err

    return True

def cmdline(command):
    process = Popen(args=command, stdout=PIPE, shell=True)
    return process.communicate()[0]

def kmaxall_cmd(d):
    os.system("kmaxall {0}/{1} > out/{1}/kmax".format(kernel_path,d))
    os.system("./kreader-hacksaw --kmax-formulas out/{0}/kmax --show-constraints --single-line --object-only --tweak > out/{0}/kmax.out".format(d))

def main(args: Namespace = parse_arguments()) -> int:
    try:
        if not load_configs(args):
            return 1

        output = ''
        for td in target_dirs:
            output = output + cmdline("find {0}/{1} -name 'Makefile' -or -name 'Kbuild'".format(kernel_path,td)).decode('utf8').strip()

        path_prefixs = set([])
        sps = output.split('\n')
        for sp in sps:
            pp = '/'.join(sp.split('/')[:-1])
            pp = pp.replace(kernel_path+'/', '')
            path_prefixs.add(pp)

        dirs = list(path_prefixs)

        for d in dirs:
            os.system("mkdir -p out/{0}".format(d))

        pool = mp.Pool(nworkers)
        pool.map(kmaxall_cmd, dirs)
        pool.close()
        pool.join()

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main(parse_arguments()))
