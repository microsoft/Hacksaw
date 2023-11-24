#!/usr/bin/env python3

import os
import sys
import shutil
import subprocess
import tempfile
from argparse import ArgumentParser, Namespace
from typing import Dict, List

image_path = ''
kernel_path = ''
inplace=False

def parse_arguments(cli_args: List[str] = None) -> Namespace:
    parser = ArgumentParser(description='Repack a bzImage (vmlinuz) file with a kernel raw image')
    parser.add_argument('-i', '--image', action='store', required=True,
                        help='bzImage file path')
    parser.add_argument('-k', '--kernel', action='store', required=True,
                        help='kernel raw image file path')
    parser.add_argument('-p', '--inplace', action='store_true',
                        help='in-place patching')
    parser.set_defaults(inplace=False)
    return parser.parse_args(args=cli_args)

def load_configs(args: Namespace) -> Dict:
    try:
        global image_path 
        image_path = os.path.realpath(args.image)
        if not os.path.exists(image_path):
            print(image_path, "does not exist", file=sys.stderr)
            return False

        global kernel_path 
        kernel_path = os.path.realpath(args.kernel)
        if not os.path.exists(kernel_path):
            print(kernel_path, "does not exist", file=sys.stderr)
            return False

    except Exception as err:
        print(err)
        if err == "Really Bad":
            raise err

    return True

unpack_helper = {
        "zst" : "zstdcat",
        "gz"  : "zcat",
        "bz2" : "bzcat",
        "xz"  : "xzcat",
        "lzma": "lzcat",
        "lz4" : "lz4cat",
        "lzo" : "lzop -fdc",
        }

comp_signature = {
        "zst" : list(b'\x28\xb5\x2f\xfd'),
        "gz"  : list(b'\x1f\x8b\x08'),
        "bz2" : list(b'\x42\x5a\x68'),
        "xz"  : list(b'\xfd\x37\x7a\x58\x5a\x00'),
        "lzma": list(b'\x5d\x00\x00\x00'),
        "lz4" : list(b'\x02\x21\x4c\x18'),
        "lzo" : list(b'\x89\x42\x5a'),
        }

def identify_compression_algorithm(bzimage):
    _, outpath = tempfile.mkstemp()

    with open(bzimage, 'rb') as f:
        data = list(f.read())
        for alg in comp_signature:
            skip = len(comp_signature[alg])

            i = 0
            while i < len(data):
                if data[i:i+skip] == comp_signature[alg]:
                    subprocess.run(f"tail -c+{i+1} {bzimage} | {unpack_helper[alg]} > {outpath} 2>/dev/null", shell=True, check=False)
                    if os.path.getsize(outpath):
                        os.unlink(outpath)
                        return (alg,i)
                i = i + skip

    os.unlink(outpath)
    return (None,None)

piggyback = list(b'\x31\xc0\x48\x8d')

def find_piggyback(bzimage):
    with open(bzimage, 'rb') as f:
        data = list(f.read())
        for i in range(0, len(data), 16):
            if data[i:i+4] == piggyback:
                return i
    return None

def compress_kernel(kernel, alg):
    _, outpath = tempfile.mkstemp()

    if alg == "zst":
        subprocess.run(f"zstd --ultra -22 -T0 -f {kernel} -o {outpath}", shell=True, check=False)
    elif alg == "gz":
        subprocess.run(f"gzip -n -9 -c {kernel} > {outpath}", shell=True, check=False)
    elif alg == "bz2":
        subprocess.run(f"bzip2 -9 -c {kernel} > {outpath}", shell=True, check=False)
    elif alg == "lzma":
        subprocess.run(f"lzma -9 -c {kernel} > {outpath}", shell=True, check=False)
    elif alg == "lzo":
        subprocess.run(f"lzop -9 -c {kernel} > {outpath}", shell=True, check=False)
    elif alg == "lz4":
        subprocess.run(f"lz4 -l -9 -c {kernel} > {outpath}", shell=True, check=False)
    elif alg == "xz":
        subprocess.run(f"xz --check=crc32 --x86 --lzma2=,dict=32MiB -c {kernel} > {outpath}", shell=True, check=False)
    else:
        return None

    return outpath

def patch_bzimage(image_path, comp_kern, start, end, inplace=False):
    patched_img=image_path + ".patched"
    shutil.copy2(image_path, patched_img)

    subprocess.run(f"dd if=/dev/zero of={patched_img} bs=1 seek={start} count={end-start} conv=notrunc", shell=True, check=False)
    subprocess.run(f"dd if={comp_kern} of={patched_img} bs=1 seek={start} conv=notrunc", shell=True, check=False)

    if inplace:
        shutil.copy2(patched_img, image_path)
        os.unlink(patched_img)

def main(args: Namespace = parse_arguments()) -> int:
    try:
        if not load_configs(args):
            return 1

        alg,idx = identify_compression_algorithm(image_path)
        if alg is None:
            print("Failed to identify a compression algorithm.")
            return 1

        piggy_idx = find_piggyback(image_path)
        if piggy_idx is None:
            print("Failed to identify piggyback data.")
            return 1

        print(f"Compression algorithm : {alg} (start: {idx}, end: {piggy_idx})")

        comp_kern = compress_kernel(kernel_path, alg)
        comp_size = os.path.getsize(comp_kern)

        if comp_size > piggy_idx-idx:
            print("Repack is not possible. Compressed patched kernel ({0}) is larger than the original kernel ({1})".format(comp_size, piggy_idx - idx))
            return 1

        if args.inplace:
            patch_bzimage(image_path, comp_kern, idx, piggy_idx, True)
        else:
            patch_bzimage(image_path, comp_kern, idx, piggy_idx)

        os.unlink(comp_kern)

    except KeyboardInterrupt:
        print("Keyboard interrupt", file=sys.stderr)
        return 1

    except Exception as err:
        print("Exception:", err, file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main(parse_arguments()))
