#!/usr/bin/env python3

import os
import sys
import shutil
import subprocess
import tempfile

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
        "xz"  : list(b'\xfd\x37\x7a\x58\x5a'),
        "lzma": list(b'\x5d\x00\x00\x00'),
        "lz4" : list(b'\x02\x21\x4c\x18'),
        "lzo" : list(b'\x89\x4c\x5a'),
        }

def identify_compression_algorithm(bzimage):
    _, outpath = tempfile.mkstemp()

    with open(bzimage, 'rb') as f:
        data = list(f.read())
        for alg in comp_signature:
            siglen = len(comp_signature[alg])

            i = 0
            while i < len(data):
                if data[i:i+siglen] == comp_signature[alg]:
                    subprocess.run(f"tail -c+{i+1} {bzimage} | {unpack_helper[alg]} > {outpath} 2>/dev/null", shell=True, check=False)
                    if os.path.getsize(outpath):
                        os.unlink(outpath)
                        return (alg,i)
                i = i+1

    os.unlink(outpath)
    return (None,None)

piggy_signature = list(b'\x31\xc0\x48\x8d')

def find_piggy(bzimage, start=0):
    if start != 0:
        start = start - (start % 16) + 16

    with open(bzimage, 'rb') as f:
        data = list(f.read())
        for i in range(start, len(data), 16):
            if data[i:i+4] == piggy_signature:
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
        subprocess.run(f"xz --check=crc32 --x86 --lzma2=,dict=32MiB,nice=128 -c {kernel} > {outpath}", shell=True, check=False)
    else:
        return None

    return outpath

def replace_comp_kernel(bzimage_path, comp_kern_path, start, end, inplace=False):
    patched_img=bzimage_path + ".patched"
    shutil.copy2(bzimage_path, patched_img)

    subprocess.run(f"dd if=/dev/zero of={patched_img} bs=1 seek={start} count={end-start} conv=notrunc", shell=True, check=False)
    subprocess.run(f"dd if={comp_kern_path} of={patched_img} bs=1 seek={start} conv=notrunc", shell=True, check=False)

    if inplace:
        shutil.copy2(patched_img, bzimage_path)
        os.unlink(patched_img)

def repack_bzimage(bzimage, kernel, inplace=False):
    if not os.path.exists(bzimage):
        print(bzimage, "does not exist", file=sys.stderr)
        return False

    if not os.path.exists(kernel):
        print(kernel, "does not exist", file=sys.stderr)
        return False

    alg,idx = identify_compression_algorithm(bzimage)
    if alg is None:
        print("Failed to identify a compression algorithm.")
        return False

    piggy_idx = find_piggy(bzimage, idx)
    if piggy_idx is None:
        print("Failed to identify piggy data.")
        return False

    print(f"Compression algorithm : {alg} (start: {idx}, end: {piggy_idx})")

    comp_kern = compress_kernel(kernel, alg)
    comp_size = os.path.getsize(comp_kern)

    if comp_size > piggy_idx-idx:
        print("Repack is not possible. Compressed patched kernel ({0}) is larger than the original kernel ({1})".format(comp_size, piggy_idx - idx))
        return False

    if inplace:
        replace_comp_kernel(bzimage, comp_kern, idx, piggy_idx, True)
    else:
        replace_comp_kernel(bzimage, comp_kern, idx, piggy_idx)

    os.unlink(comp_kern)
    return True
