#!/usr/bin/env python3
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

import os
import sys
import subprocess
import threading
import glob
import re
from collections import defaultdict
from argparse import ArgumentParser, Namespace
from typing import Dict, List

kernel_path = ''

exports = set([])

def parse_arguments(cli_args: List[str] = None) -> Namespace:
    parser = ArgumentParser(description='Get minimal kernel configuration expressions for each object file')
    parser.add_argument('-k', '--kernel-path', action='store', required=True,
                        help='kernel source path')
    return parser.parse_args(args=cli_args)

def load_configs(args: Namespace) -> Dict:
    try:
        global kernel_path
        kernel_path=os.path.realpath(args.kernel_path)
        if not os.path.exists(kernel_path):
            print(kernel_path, "does not exist", file=sys.stderr)
            return False

    except Exception as err:
        print(err)
        if err == "Really Bad":
            raise err

    return True

def main(args: Namespace = parse_arguments()) -> int:
    try:
        if not load_configs(args):
            return 1

        globs = glob.glob(kernel_path + "/**/built-in.a", recursive=True)
        for builtin in globs:
            with open(builtin) as file:
                for line in file:
                    l = line.rstrip()
                    if len(l) > 0 and l[-1] == '/' and len(l.split('/')) == 2:
                        print('/'.join(builtin.split('/')[:-1]) + '/' + l.split('/')[0]) 

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main(parse_arguments()))
