'''
Branch unit
1. one-bit predictor + 8-entry BTB (index: low 3 bits of the word address of the PC)
   -- prediction is done in the ISSUE stage
2. branch resolution (end of EX) and misprediction recovery
   -- recover the RAT
   -- clear the reservation stations / functional units / queues of the wrong instructions
   -- clear the ROB entries after the branch
   -- these actions take one cycle: a misprediction detected in cycle n restarts fetch in cycle n+2
'''
BTB_SIZE = 8

# function: build an empty BTB; entry = (branch PC, target PC, 1-bit prediction: taken)
def build_btb():
    return [None] * BTB_SIZE

# function: predict at issue; returns (taken, next PC)
def predict(btb, pc):
    entry = btb[pc % BTB_SIZE]
    if entry is not None and entry[0] == pc and entry[2]:
        return True, entry[1]
    return False, pc + 1

# function: train the predictor with the outcome of a resolved branch
def update_btb(btb, pc, target, taken):
    btb[pc % BTB_SIZE] = (pc, target, taken)

# function: rebuild the RAT from the architectural registers and the surviving ROB entries
def rebuild_rat(ROB, rat_int, rat_fp, reg_int, reg_fp):
    rat_int[:] = reg_int
    rat_fp[:] = reg_fp
    for entry in ROB:
        dest = entry.dest_tag
        if (type(dest) == str) and (dest[0] in 'RF') and (dest != 'R0'):
            item = entry.value if len(entry.cdb) != 0 else entry.ROB_tag
            if dest[0] == 'F':
                rat_fp[int(dest[1:])] = item
            else:
                rat_int[int(dest[1:])] = item

# function: remove everything that belongs to the instructions younger than the branch
def squash(index, ROB, rs_list, fu_list, results_buffer, cdb,
           ld_sd_queue, ld_sd_exe, ld_sd_mem):
    while len(ROB) > index + 1:
        ROB.pop()
    alive = set(entry.ROB_tag for entry in ROB)
    # reservation stations (this also clears their wait-for tags)
    for rs in rs_list:
        for element in rs:
            if (element.busy == 1) and (element.dest_tag not in alive):
                element.busy = 0
    # functional units and results waiting for the CDB
    for fu in fu_list:
        keep = [element for element in fu if element.dest_tag in alive]
        fu.clear()
        fu.extend(keep)
    keep = [element for element in results_buffer if element.dest_tag in alive]
    results_buffer.clear()
    results_buffer.extend(keep)
    if (cdb.valid == 1) and (cdb.dest_tag not in alive):
        cdb.valid = 0
    # load/store queue and the units working on its entries
    removed = [element.ld_sd_tag for element in ld_sd_queue if element.dest_tag not in alive]
    keep = [element for element in ld_sd_queue if element.dest_tag in alive]
    ld_sd_queue.clear()
    ld_sd_queue.extend(keep)
    if (ld_sd_exe.busy == 1) and (ld_sd_exe.dest_tag in removed):
        ld_sd_exe.busy = 0
    # stores only access memory when they commit, so only a load can be on the wrong path
    if (ld_sd_mem.busy == 1) and (ld_sd_mem.op == 'Ld') and (ld_sd_mem.dest_tag not in alive):
        ld_sd_mem.busy = 0

# function: process the branches that finished EX in this cycle (oldest first)
def resolve_branches(cycle, PC, ROB, btb, rs_list, fu_list, results_buffer, cdb,
                     ld_sd_queue, ld_sd_exe, ld_sd_mem, rat_int, rat_fp, reg_int, reg_fp):
    pending = PC.resolved
    PC.resolved = []
    order = [e.ROB_tag for e in ROB]
    for tag in sorted(pending, key=order.index):
        position = [e.ROB_tag for e in ROB]
        if tag not in position:     # already squashed by an older misprediction
            continue
        index = position.index(tag)
        entry = ROB[index]
        taken = entry.value
        target = entry.PC + 1 + entry.dest_tag
        update_btb(btb, entry.PC, target, taken)
        if taken != entry.pred:
            squash(index, ROB, rs_list, fu_list, results_buffer, cdb,
                   ld_sd_queue, ld_sd_exe, ld_sd_mem)
            rebuild_rat(ROB, rat_int, rat_fp, reg_int, reg_fp)
            PC.PC = target if taken else entry.PC + 1
            PC.resume = cycle + 2
