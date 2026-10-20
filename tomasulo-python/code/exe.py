# Qing 
# 24th May 2017

''' 
1. calculate valid instructions
    -- for ALU instructions, write results into fu_results, remove that fu entry  
    -- for LD/SD, write address result immediately back to ld_sd_queue
2. fetch instructions into function unit with spare space
    -- remove ALU instructions from rs
    -- don't remove ld/sd instructions
'''
from init import fu_entry, fu_result

# function: check rs and return valid instruction index
def check_valid_ins_in_rs(rs):
    index = -1
    if len(rs)!=0:
        for i in range(len(rs)):
            if (rs[i].valid_1st==1)&(rs[i].valid_2nd==1)&(rs[i].busy==1):
                index = i
                break
    return index

# function: check ld_sd_queue and return valid instruction index
def check_valid_ins_in_ldsd(ldsd):
    index = -1
    if len(ldsd)!=0:
        for i in range(len(ldsd)):
            if (ldsd[i].valid==1) & (ldsd[i].ready==0):
                index = i
                break
    return index

# function: add entry into fu 
def add_entry_into_fu(fu, ins_in_rs):
    fu[-1].cycle = 0
    fu[-1].op = ins_in_rs.op
    fu[-1].value1 = ins_in_rs.value_1st
    fu[-1].value2 = ins_in_rs.value_2nd
    fu[-1].dest_tag = ins_in_rs.dest_tag

# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            break
    return index

# function: functional units execution
# every operation in the unit advances by exactly one cycle; operations that are done leave the unit
# returns (number of operations that started executing in this cycle, number that finished)
def fu_exe(fu, fu_results, ROB, time_fu, cycle, PC):
    started = 0
    for element in fu:
        element.cycle += 1
        # write starting cycle
        if element.cycle == 1:
            ROB[find_ROB_entry(ROB, element.dest_tag)].exe.append(cycle)
            started += 1
    finished = fu_finish(fu, fu_results, ROB, time_fu, cycle, PC)
    return started, finished

# function: finish the operations that completed their last execution cycle; returns their number
def fu_finish(fu, fu_results, ROB, time_fu, cycle, PC):
    finished = 0
    for element in list(fu):
        if element.cycle == time_fu:
            index = find_ROB_entry(ROB, element.dest_tag)
            ROB[index].exe.append(cycle)
            if (element.op=='Bne')|(element.op=='Beq'):
                # the branch is resolved here; the branch unit handles the result after EX
                if element.op == 'Bne':
                    ROB[index].value = (element.value1 != element.value2)
                else:
                    ROB[index].value = (element.value1 == element.value2)
                PC.resolved.append(element.dest_tag)
            else:
                # calculation result
                fu_results.append(fu_result())
                fu_results[-1].dest_tag = element.dest_tag
                if (element.op=='Add')|(element.op=='Add.d')|(element.op=='Addi'):
                    fu_results[-1].value = element.value1 + element.value2
                elif (element.op=='Sub')|(element.op=='Sub.d'):
                    fu_results[-1].value = element.value1 - element.value2
                elif (element.op=='Mult.d'):
                    fu_results[-1].value = element.value1 * element.value2
            # remove from fu 
            fu.remove(element)
            finished += 1
    return finished

# function: move valid instructions from rs into the functional units (at most nfu per cycle)
# started, finished: operations that already started / finished executing in this cycle
# pipelined: an unpipelined unit is busy until its operation has finished its last cycle
def fu_fetch_from_rs(fu, fu_results, rs, ROB, time_fu, cycle, PC, nfu, started, finished, pipelined):
    deferred = 0
    for index in range(len(rs)):
        if not ((rs[index].valid_1st==1)&(rs[index].valid_2nd==1)&(rs[index].busy==1)):
            continue
        if (not pipelined) and (len(fu) + finished >= nfu):
            break
        # check if it's a waiting instruction (issued in this cycle, executes in the next one)
        waiting = ROB[find_ROB_entry(ROB, rs[index].dest_tag)].issue[0] >= cycle
        if waiting:
            if deferred >= nfu:
                continue
        elif started >= nfu:
            continue
        fu.append(fu_entry())
        add_entry_into_fu(fu, rs[index])
        # remove ins from rs 
        rs[index].busy = 0
        if waiting:
            deferred += 1
        else:
            fu[-1].cycle = 1
            ROB[find_ROB_entry(ROB, fu[-1].dest_tag)].exe.append(cycle)
            started += 1
            finished += fu_finish(fu, fu_results, ROB, time_fu, cycle, PC)

# function: ld_sd_execution 
def ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle):
    if ld_sd_exe.busy == 1:
        # write down starting cycle
        if ld_sd_exe.cycle == 0:            
            for element in ld_sd_queue:
                if element.ld_sd_tag == ld_sd_exe.dest_tag:
                    break
            index = find_ROB_entry(ROB, element.dest_tag)
            ROB[index].exe.append(cycle)
            # execute 
            ld_sd_exe.cycle += 1
        else:
            ld_sd_exe.cycle += 1
        # write address back to ld_sd_queue
        if ld_sd_exe.cycle == time_ld_sd_exe:
            address = ld_sd_exe.value1 + ld_sd_exe.value2
            for element in ld_sd_queue:
                if element.ld_sd_tag == ld_sd_exe.dest_tag:
                    element.address = address
                    element.ready = 1
                    break
            # write down finish cycle
            index = find_ROB_entry(ROB, element.dest_tag)
            ROB[index].exe.append(cycle)
            ld_sd_exe.busy = 0

# function: execution
def exe(fu_int_adder, time_fu_int_adder, nfu_int_adder,
        fu_fp_adder, time_fu_fp_adder, nfu_fp_adder,
        fu_fp_multi, time_fu_fp_multi, nfu_fp_multi, results_buffer,
        rs_int_adder, rs_fp_adder, rs_fp_multi, 
        ld_sd_exe, time_ld_sd_exe, ld_sd_queue,
        cycle, ROB, PC):
    '''execution in fu and ld_sd address calculation'''
    ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle) 
    # functional units 
    started_int, finished_int = fu_exe(fu_int_adder, results_buffer, ROB, time_fu_int_adder, cycle, PC)
    started_fp_adder, finished_fp_adder = fu_exe(fu_fp_adder, results_buffer, ROB, time_fu_fp_adder, cycle, PC)
    started_fp_multi, finished_fp_multi = fu_exe(fu_fp_multi, results_buffer, ROB, time_fu_fp_multi, cycle, PC)
    '''fetch instructions from rs and ld_sd_queue'''
    # from ld_sd_queue
    # check valid ins in ld_sd_queue 
    index = check_valid_ins_in_ldsd(ld_sd_queue)
    # put ins into ld_sd_exe
    if (index>=0)&(ld_sd_exe.busy==0):
        ld_sd_exe.busy = 1
        ld_sd_exe.cycle = 0
        ld_sd_exe.value1 = ld_sd_queue[index].reg_value
        ld_sd_exe.value2 = ld_sd_queue[index].immediate
        ld_sd_exe.dest_tag = ld_sd_queue[index].ld_sd_tag
        if ROB[find_ROB_entry(ROB, ld_sd_queue[index].dest_tag)].issue[0] < cycle:
            ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle)
    # from rs 
    # the integer adder is not pipelined, the fp units are
    fu_fetch_from_rs(fu_int_adder, results_buffer, rs_int_adder, ROB, time_fu_int_adder, cycle, PC,
                     nfu_int_adder, started_int, finished_int, False)
    fu_fetch_from_rs(fu_fp_adder, results_buffer, rs_fp_adder, ROB, time_fu_fp_adder, cycle, PC,
                     nfu_fp_adder, started_fp_adder, finished_fp_adder, True)
    fu_fetch_from_rs(fu_fp_multi, results_buffer, rs_fp_multi, ROB, time_fu_fp_multi, cycle, PC,
                     nfu_fp_multi, started_fp_multi, finished_fp_multi, True)
