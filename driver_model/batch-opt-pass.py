#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import multiprocessing as mp
import subprocess
from argparse import ArgumentParser, Namespace
from typing import Dict, List


kernel_path = ''
pass_object = ''
pass_name = ''
nworkers = 1

def parse_arguments(cli_args: List[str] = None) -> Namespace:
    parser = ArgumentParser(description='Get minimal kernel configuration expressions for each object file')
    parser.add_argument('-k', '--kernel-path', action='store', required=True,
                        help='kernel source path')
    parser.add_argument('-o', '--pass-object', action='store', required=True,
                        help='pass object file')
    parser.add_argument('-p', '--pass-name', action='store', required=True,
                        help='pass name')
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

        global pass_object
        pass_object = args.pass_object

        global pass_name
        pass_name = args.pass_name

        global nworkers
        if args.num_workers != None:
            nworkers = int(args.num_workers)

    except Exception as err:
        print(err)
        if err == "Really Bad":
            raise err

    return True

def extract_bc_cmd(bc):
    os.system("opt -load {0} -enable-new-pm=0 --{1} -o /dev/null {2}".format(pass_object, pass_name, bc))

def main(args: Namespace = parse_arguments()) -> int:
    try:
        if not load_configs(args):
            return 1

        p = subprocess.run(['find', kernel_path, '-name', '*.hacksaw.bc'], capture_output=True, text=True)
        bcs = p.stdout.split()

        pool = mp.Pool(nworkers)
        pool.map(extract_bc_cmd, bcs)
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
