#!/usr/bin/env python3

import capstone
import subprocess

def disasm_test(fn, off):
    patch_range = {}
    #d = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    #insn = d.disasm(data[off:], len(data[off:]))
    #help(insn)
    out = subprocess.check_output(['objdump', '-D', f'--start-address={hex(off)}', f'{fn}'])
    expected_dis = set()
    start = False
    print(out.decode('latin-1').split('\n')[:30])
    for line in out.decode('latin-1').split('\n'):
        line = line.strip()
        if not line:
            continue
        if not start and line.startswith(f'{hex(off)[2:]}'):
            start = True
        if start:
            if off in expected_dis:
                expected_dis.remove(off)
            if len(line.split('\t')) < 3:
                continue
            _,by,insn = line.split('\t')
            insn = insn.strip()
            by = by.strip().split()
            print(insn)
            print(by)
            print(len(by))
            patch_range[off] = len(by)
            off += len(by)
            if insn.startswith('j'):
                if (not insn.split()[1].strip().isnumeric()) and len(expected_dis) == 0:
                    break
                jmpaddr = int(insn.split()[1].strip(), 16)
                if jmpaddr > off:
                    expected_dis.add(jmpaddr)
            if insn.startswith('ret') and len(expected_dis) == 0:
                break
    return patch_range

def get_text_rel(fn):
    out = subprocess.check_output(' '.join(['readelf', '-S', f'{fn}', '|', 'grep', '"\.text"']), shell=True)
    for line in out.decode('latin-1').split('\n'):
        line = line.strip()
        if '.text' in line.split():
            data = line.split('.text')[1].strip()
            text_va = int(data.split()[1], 16)
            text_off = int(data.split()[2], 16)
            return text_off, text_va
    return (0, 0)

def disasm(fn, off, raw_off=False, text_rel=None):
    text_va = 0
    text_off = 0
    if not raw_off and not text_rel:
        text_off, text_va = get_text_rel(fn)
    if text_rel:
        text_off, text_va = text_rel

    off += text_off
    patch_range = {}
    with open(fn, 'rb') as fd:
        data = fd.read()
    d = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    expected_dis = set()
    #print("DEBUG disas ", hex(off), hex(text_va), hex(text_off), hex(len(data)))
    for insn in d.disasm(data[off:off+16], text_va):
        #print(insn)
        if off in expected_dis:
            expected_dis.remove(off)
        #patch_range[insn.address] = insn.size
        patch_range[off] = insn.size
        #print(hex(insn.address), hex(off), insn.mnemonic, insn.op_str)
        off += insn.size
        if insn.mnemonic.startswith('j'):
            if (not insn.op_str.isnumeric()) and len(expected_dis) == 0:
                break
            jmpaddr = int(insn.op_str, 16)
            if jmpaddr > insn.address:
                expected_dis.add(jmpaddr - text_va + text_off)
        if insn.mnemonic.startswith('ret') and len(expected_dis) == 0:
            break
    merged_result = {}
    prev = None
    nxt = None
    for o in sorted(patch_range.keys()):
        l = patch_range[o]
        if not nxt:
            merged_result[o] = l
            nxt = o + l
            prev = o
        else:
            if o == nxt:
                merged_result[prev] += l
                nxt += l
            else:
                merged_result[o] = l
                nxt = o + l
                prev = o
    return merged_result

if __name__ == '__main__':
    data = b"\x55\x48\x8b\x05\xb8\x13\x00\x00"
    #patch = disasm_test('./vmlinix', 0xffffffff8102b390)
    patch = disasm('./vmlinix', 0x2b390)
    for i in patch:
        print(hex(i), patch[i])
