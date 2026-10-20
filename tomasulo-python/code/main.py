# Qing 
# 21st May 2017 

import sys
from copy import deepcopy
from collections import deque, namedtuple
from init import read_input, InputError, build_rs, ld_sd_entry, ld_sd_exe, ld_sd_mem, cdb, ROB_entry, PC
from print_status import ps, pss
from issue import issue, check_rs_space
from exe import exe 
from mem import mem
from wb import wb 
from commit import commit
from branch import build_btb, resolve_branches

MAX_CYCLES = 100000

'''initialize'''
# read configuration, initial state and instructions from the input file
try:
    config, instructions = read_input(sys.argv[1] if len(sys.argv) > 1 else 'test_case.txt')
except (InputError, OSError) as error:
    sys.exit('error: %s' % error)
'''initialize regs, RAT, memory''' 
# integer REG
reg_int = config['reg_int']
rat_int = deepcopy(reg_int)
# fp REG
reg_fp = config['reg_fp']
rat_fp = deepcopy(reg_fp)
# memory 
memory = config['memory']
'''intialize reservation stations'''
# integer adder rs 
size_rs_int_adder = config['rs_int_adder']
rs_int_adder = build_rs(size_rs_int_adder)
# fp adder rs
size_rs_fp_adder = config['rs_fp_adder']
rs_fp_adder = build_rs(size_rs_fp_adder)
# fp multiplier rs
size_rs_fp_multi = config['rs_fp_multi']
rs_fp_multi = build_rs(size_rs_fp_multi)
'''initilize function unit'''
# integer adder 
fu_int_adder = deque()
time_fu_int_adder = config['ex_int_adder']
nfu_int_adder = config['nfu_int_adder']
# fp adder 
fu_fp_adder = deque()
time_fu_fp_adder = config['ex_fp_adder']
nfu_fp_adder = config['nfu_fp_adder']
# fp multiplier
fu_fp_multi = deque()
time_fu_fp_multi = config['ex_fp_multi']
nfu_fp_multi = config['nfu_fp_multi']
'''initialize load/store queue'''
ld_sd_queue = deque()
size_ld_sd_queue = config['rs_ld_sd']
ld_sd_exe = ld_sd_exe()
ld_sd_exe.busy = 0
time_ld_sd_exe = config['ex_ld_sd']
ld_sd_mem = ld_sd_mem()
ld_sd_mem.busy = 0
time_ld_sd_mem = config['mem_cycles']
'''initialize ROB'''
ROB = deque()
size_ROB = config['rob_size']
'''initialize CDB'''
results_buffer = deque()
cdb = cdb()
cdb.valid = 0
'''initialize branch predictor (1-bit, 8-entry BTB)'''
btb = build_btb()
issue_width = config['issue_width']
"""issue first instruction"""
# instruction pointer 
PC = PC()
PC.PC = 0
PC.valid = 1 
PC.resume = 1   # first cycle in which instructions can be fetched
PC.resolved = []  # branches that finished EX in the current cycle
cycle = 1

# print title 
item = ''.ljust(30)
item += 'ISSUE'.ljust(15)
item += 'EXE'.ljust(15)
item += 'MEM'.ljust(15)
item += 'WB'.ljust(15)
item += 'COMMIT'.ljust(15)
print (item)

# main
while (len(ROB)>0)|(0<=PC.PC<len(instructions))|(ld_sd_mem.busy==1):
    if cycle > MAX_CYCLES:
        sys.exit('error: more than %d cycles, the program probably never ends' % MAX_CYCLES)
    
    '''ISSUE stage'''
    if (0<=PC.PC<len(instructions))&(cycle>=PC.resume):
        issue(cycle, PC, instructions, ROB, size_ROB, 
                rs_int_adder, 
                rs_fp_adder, 
                rs_fp_multi, 
                ld_sd_queue, size_ld_sd_queue, 
                rat_int, rat_fp, btb, issue_width)

    '''EXE stage'''
    exe(fu_int_adder, time_fu_int_adder, nfu_int_adder,
        fu_fp_adder, time_fu_fp_adder, nfu_fp_adder,
        fu_fp_multi, time_fu_fp_multi, nfu_fp_multi, results_buffer,  
        rs_int_adder, rs_fp_adder, rs_fp_multi, 
        ld_sd_exe, time_ld_sd_exe, ld_sd_queue,
        cycle, ROB, PC)

    '''branch resolution and misprediction recovery'''
    resolve_branches(cycle, PC, ROB, btb, 
        [rs_int_adder, rs_fp_adder, rs_fp_multi], 
        [fu_int_adder, fu_fp_adder, fu_fp_multi], results_buffer, cdb,
        ld_sd_queue, ld_sd_exe, ld_sd_mem, rat_int, rat_fp, reg_int, reg_fp)

    '''MEM stage'''
    mem(ld_sd_queue, ld_sd_mem, time_ld_sd_mem, results_buffer,
        memory, ROB, cycle)

    '''CDB stage'''
    wb(cdb, rat_int, rat_fp, 
        rs_int_adder, rs_fp_adder, rs_fp_multi,
        ld_sd_queue, ROB, cycle,
        results_buffer) 
    
    '''COMMIT stage'''
    commit(ROB, reg_int, reg_fp, cycle, instructions)
    
    # cycle number 
    cycle +=1  

# results: registers and non-zero memory
def fmt(items, width=9):
    return ''.join(str(x).ljust(width) for x in items)
print()
print('REGISTER VALUES')
for name, regs in (('R', reg_int), ('F', reg_fp)):
    print(' '*7 + fmt('%s%d' % (name, i) for i in range(32)))
    print('value: ' + fmt(regs))
print()
print('NON-ZERO MEMORY VALUES')
print('Addresses'.ljust(12) + 'Values')
for address in range(len(memory)):
    if memory[address] != 0:
        print(str(address).ljust(12) + str(memory[address]))
