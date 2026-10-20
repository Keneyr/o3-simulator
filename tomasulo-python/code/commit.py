# Qing 
# 29th may 2017
'''
1. commit ROB_buffer
2. fetch header into ROB_buffer
'''

# function: print ROB entry 
def print_ROB(entry, instructions):
    item = instructions[entry.PC].ljust(30)
    item += str(entry.issue).ljust(15) 
    item += str(entry.exe).ljust(15) 
    item += str(entry.mem).ljust(15)
    item += str(entry.cdb).ljust(15)
    item += str(entry.commit)
    print(item)
# function: modify architectual reg
def modify_arch_reg(entry, reg_int, reg_fp):
    if entry.dest_tag[0] == 'F':
        reg_fp[int(entry.dest_tag[1:])] = entry.value
    elif (entry.dest_tag[0] == 'R') and (entry.dest_tag != 'R0'):
        reg_int[int(entry.dest_tag[1:])] = entry.value
    else:
        pass

# function: check if the ROB entry is a branch
def is_branch(entry, instructions):
    return instructions[entry.PC].split(' ')[0] in ('Bne', 'Beq')

# function: commit
def commit(ROB, reg_int, reg_fp, cycle, instructions):
    if len(ROB)>0:
        if is_branch(ROB[0], instructions):
            if len(ROB[0].exe)==2: # resolved (start and end of EX)
                ROB[0].commit.append(cycle+1)
                entry = ROB.popleft()
                print_ROB(entry, instructions)
        if (len(ROB)>0) and (not is_branch(ROB[0], instructions)):
            if len(ROB[0].cdb)!=0: # broadcasted instructions
                ROB[0].commit.append(cycle+1)
                entry = ROB.popleft()
                modify_arch_reg(entry, reg_int, reg_fp)
                print_ROB(entry, instructions)
            elif len(ROB[0].commit)!=0: # Sd
                entry = ROB.popleft()
                print_ROB(entry, instructions)
                if len(ROB)>0:
                    if (len(ROB[0].cdb)!=0) and (not is_branch(ROB[0], instructions)): # broadcasted instructions
                        ROB[0].commit.append(cycle+1)
                        entry = ROB.popleft()
                        modify_arch_reg(entry, reg_int, reg_fp)
                        print_ROB(entry, instructions)
            else:
                pass
