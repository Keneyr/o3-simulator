# Qing 
# 21st May 2017 

import re
from collections import namedtuple

'''define data types'''
# reservation station 
def rs_entry():
    rs_entry = namedtuple('rs_entry', 'busy, op, tag_1st, value_1st, valid_1st, tag_2nd, value_2nd, valid_2nd, dest_tag')
    temp = rs_entry
    return temp 
# functional unit 
def fu_entry():
    fu_entry = namedtuple('fu_entry', 'cycle, op, value1, value2, dest_tag')
    temp = fu_entry
    return temp
# function result 
def fu_result():
    fu_result = namedtuple('fu_result', 'value, dest_tag')
    temp = fu_result
    return temp
# ld/sd entry
def ld_sd_entry():
    ld_sd_entry = namedtuple('ld_sd_entry', 'ld_sd_tag, ready, op, address, data, dest_tag, immediate, reg_tag, reg_value, valid')
    temp = ld_sd_entry
    return temp
# ld/sd exe
def ld_sd_exe():
    ld_sd_exe = namedtuple('ld_sd_exe', 'busy, cycle, value1, value2, dest_tag')
    temp = ld_sd_exe
    return temp
# ld/sd mem
def ld_sd_mem():
    ld_sd_mem = namedtuple('ld_sd_mem', 'busy, cycle, op, data, address, dest_tag')
    temp = ld_sd_mem
    return temp
# cdb
def cdb():
    cdb = namedtuple('cdb', 'valid, value, dest_tag')
    temp = cdb
    return temp
# ROB_entry 
def ROB_entry():
    ROB_entry = namedtuple('ROB_entry', 'ROB_tag, PC, value, dest_tag, issue, exe, mem, cdb, commit, pred')
    temp = ROB_entry
    temp.issue = []
    temp.exe = []
    temp.mem = []
    temp.cdb = []
    temp.commit =[]
    return temp
# PC 
def PC():
    PC = namedtuple('PC', 'PC, valid, resume, resolved')
    temp = PC
    return temp
# function: read instructions (instruction-only file)
def read_instruction(codefile):
    with open(codefile) as f:
            instructions = f.read().splitlines()
    return instructions

# ---------------------------------------------------------------------------
# input file: hardware configuration, initial state and program
# ---------------------------------------------------------------------------
UNITS = {'integer adder': 'int_adder', 'fp adder': 'fp_adder',
         'fp multiplier': 'fp_multi', 'load/store unit': 'ld_sd'}
OPS = {'ld': 'Ld', 'sd': 'Sd', 'beq': 'Beq', 'bne': 'Bne', 'add': 'Add', 'add.d': 'Add.d',
       'addi': 'Addi', 'sub': 'Sub', 'sub.d': 'Sub.d', 'mult.d': 'Mult.d'}

class InputError(Exception):
    pass

def _reg(token, kind, lineno):
    m = re.fullmatch(r'([rf])(\d+)', token.lower())
    if not m or m.group(1).upper() != kind or int(m.group(2)) > 31:
        raise InputError('line %d: bad %s register "%s"' % (lineno, kind, token))
    return kind + str(int(m.group(2)))

# function: turn "add.d f1, f2, f3" into the canonical form used by the simulator: "Add.d F1 F2 F3"
def normalize_instruction(line, lineno):
    parts = line.split(None, 1)
    op = OPS.get(parts[0].lower())
    rest = parts[1] if len(parts) > 1 else ''
    if op is None:
        raise InputError('line %d: unknown instruction "%s"' % (lineno, line))
    if op in ('Ld', 'Sd'):
        m = re.fullmatch(r'\s*(\w+)\s*,?\s*(-?\d+)\s*\(\s*(\w+)\s*\)\s*', rest)
        if not m:
            raise InputError('line %d: bad operands "%s"' % (lineno, line))
        return '%s %s %s(%s)' % (op, _reg(m.group(1), 'F', lineno), m.group(2),
                                 _reg(m.group(3), 'R', lineno))
    t = [x for x in re.split(r'[\s,]+', rest.strip()) if x]
    if len(t) != 3:
        raise InputError('line %d: bad operands "%s"' % (lineno, line))
    if op in ('Beq', 'Bne'):
        if not re.fullmatch(r'-?\d+', t[2]):
            raise InputError('line %d: bad branch offset "%s"' % (lineno, t[2]))
        return '%s %s %s %d' % (op, _reg(t[0], 'R', lineno), _reg(t[1], 'R', lineno), int(t[2]))
    if op == 'Addi':
        if not re.fullmatch(r'-?\d+', t[2]):
            raise InputError('line %d: bad immediate "%s"' % (lineno, t[2]))
        return 'Addi %s %s %d' % (_reg(t[0], 'R', lineno), _reg(t[1], 'R', lineno), int(t[2]))
    kind = 'F' if op.endswith('.d') else 'R'
    return '%s %s %s %s' % (op, _reg(t[0], kind, lineno), _reg(t[1], kind, lineno),
                            _reg(t[2], kind, lineno))

# function: read the input file
# returns (config, instructions); config keys: rs_<unit>, ex_<unit>, nfu_<unit>, mem_cycles,
# rob_size, issue_width, reg_int, reg_fp, memory
def read_input(path):
    cfg = {'rs_int_adder': 2, 'ex_int_adder': 1, 'nfu_int_adder': 1,
           'rs_fp_adder': 3, 'ex_fp_adder': 3, 'nfu_fp_adder': 1,
           'rs_fp_multi': 2, 'ex_fp_multi': 20, 'nfu_fp_multi': 1,
           'rs_ld_sd': 3, 'ex_ld_sd': 1, 'mem_cycles': 4, 'nfu_ld_sd': 1,
           'rob_size': 128, 'issue_width': 1}
    reg_int = [0] * 32
    reg_fp = [0.0] * 32
    memory = [0.0] * 256
    instructions = []
    with open(path) as f:
        lines = f.read().splitlines()
    for lineno, raw in enumerate(lines, 1):
        line = raw.split('#')[0].strip()
        if not line:
            continue
        low = line.lower()
        unit = next((u for u in UNITS if low.startswith(u)), None)
        if unit:
            n = [int(x) for x in re.findall(r'\d+', line[len(unit):])]
            name = UNITS[unit]
            if name == 'ld_sd' and len(n) == 4:
                cfg['rs_ld_sd'], cfg['ex_ld_sd'], cfg['mem_cycles'], cfg['nfu_ld_sd'] = n
            elif name != 'ld_sd' and len(n) == 3:
                cfg['rs_' + name], cfg['ex_' + name], cfg['nfu_' + name] = n
            else:
                raise InputError('line %d: bad unit configuration "%s"' % (lineno, line))
            continue
        m = re.fullmatch(r'(rob entries|issue width)\s*=\s*(\d+)', low)
        if m:
            cfg[m.group(1).replace('rob entries', 'rob_size').replace('issue width', 'issue_width')] = int(m.group(2))
            continue
        if '=' in line:
            for item in line.split(','):
                m = re.fullmatch(r'\s*(r\d+|f\d+|mem\[\d+\])\s*=\s*([-+0-9.eE]+)\s*', item.lower())
                if not m:
                    raise InputError('line %d: bad initialization "%s"' % (lineno, item.strip()))
                name, value = m.group(1), m.group(2)
                if name[0] == 'm':
                    addr = int(name[4:-1])
                    if not 0 <= addr < 256:
                        raise InputError('line %d: memory address %d out of range' % (lineno, addr))
                    memory[addr] = float(value)
                elif name[0] == 'r':
                    if int(name[1:]) > 31 or (int(name[1:]) == 0 and float(value) != 0):
                        raise InputError('line %d: bad or read-only register "%s"' % (lineno, name))
                    reg_int[int(name[1:])] = int(float(value))
                else:
                    if int(name[1:]) > 31:
                        raise InputError('line %d: bad register "%s"' % (lineno, name))
                    reg_fp[int(name[1:])] = float(value)
            continue
        instructions.append(normalize_instruction(line, lineno))
    if not 1 <= cfg['issue_width'] <= 4:
        raise InputError('issue width must be between 1 and 4')
    cfg['reg_int'], cfg['reg_fp'], cfg['memory'] = reg_int, reg_fp, memory
    return cfg, instructions
# function: build rs
def build_rs(num):
    rs = []
    for _ in range(num):
        temp = rs_entry()
        temp.busy = 0
        rs.extend([temp])
    return rs

