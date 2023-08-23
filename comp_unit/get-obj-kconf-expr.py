#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import multiprocess as mp
from argparse import ArgumentParser, Namespace
from typing import Dict, List

dirs=[
    "arch/x86",
    "block",
    "certs",
    "drivers",
    "fs",
    "init",
    "io_uring",
    "ipc",
    "kernel",
    "lib",
    "mm",
    "net",
    "security",
    "sound",
    "usr",
    "virt"
]

kernel_path = ''
output_path = ''
nworkers = 1

def parse_arguments(cli_args: List[str] = None) -> Namespace:
    parser = ArgumentParser(description='Get minimal kernel configuration expressions for each object file')
    parser.add_argument('-k', '--kernel-path', action='store', required=True,
                        help='kernel source path')
    parser.add_argument('-o', '--output-path', action='store',
                        help='output path')
    parser.add_argument('-n', '--num-workers', action='store',
                        help='the number of worker threads')
    return parser.parse_args(args=cli_args)

def load_configs(args: Namespace) -> Dict:
    try:
        global kernel_path
        kernel_path=os.path.realpath(args.kernel_path)
        if not os.path.exists(kernel_path):
            print(kernel_path, "does not exist", file=sys.stderr)
            return False

        global output_path
        if args.output_path != None:
            if args.output_path[0] == '/':
                output_path = args.output_path
            else:
                output_path = os.getcwd() + '/' + args.output_path
        else:
            output_path = os.getcwd() + '/out'

        global nworkers
        if args.num_workers != None:
            nworkers = int(args.num_workers)

    except Exception as err:
        print(err)
        if err == "Really Bad":
            raise err

    return True

def kmaxall_cmd(d):
    cwd = os.getcwd()
    os.chdir(kernel_path)
    os.system("kmaxall -B {0} > {1}/{0}/kmax".format(d,output_path))

    os.chdir(cwd)
    os.system("./kreader-hacksaw --kmax-formulas {1}/{0}/kmax --show-constraints --single-line --object-only --tweak > {1}/{0}/kmax.out".format(d,output_path))

def main(args: Namespace = parse_arguments()) -> int:
    try:
        if not load_configs(args):
            return 1

        for d in dirs:
            os.system("mkdir -p {0}/{1}".format(output_path,d))

        pool = mp.Pool(nworkers)
        pool.map(kmaxall_cmd, dirs)
        pool.close()
        pool.join()

        os.system("find " + output_path + " -name 'kmax.out' -exec cat {} \; | sort | uniq")

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main(parse_arguments()))
