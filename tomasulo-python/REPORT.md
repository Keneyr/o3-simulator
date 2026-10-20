# Report: multi-issue extension of the Python Tomasulo simulator

## 1. What was added (all in `code/`)

| File | Change |
|---|---|
| `main.py` | Reads all configuration (unit table, ROB size, issue width, registers, memory, program) from the input file. Calls the new branch-resolution step each cycle. Prints the stage table, register values and non-zero memory. |
| `init.py` | New input parser (`read_input`) for the handbook format. `Issue width` must be 1–4 (default 1). ROB entries get a `pred` field. |
| `issue.py` | The old single-instruction `issue` became `issue_one`. The new `issue` calls it up to *issue width* times per cycle, in program order, and stops at the first stall (full ROB, RS or load/store queue). A branch predicted taken ends the group. Added `Beq`/`Bne` handling with prediction at ISSUE. |
| `branch.py` (new) | 1-bit predictor, 8-entry BTB indexed by `PC mod 8`, not-taken on a BTB miss. On a misprediction found in cycle n it squashes younger instructions (ROB, RS, FUs, CDB buffer, load/store queue), rebuilds the RAT and restarts fetch in cycle n+2. |
| `exe.py` | Several FUs per type; the integer adder is unpipelined, the FP units are pipelined. Branches are resolved at the end of EX. |
| `commit.py` | Branches commit once resolved. R0 is never written. |

Bugs in the original code that had to be fixed for multi-issue to work:

* `exe.py`: operations already in flight were advanced twice per cycle. Each is now advanced once.
* `exe.py`: the load/store address unit only counted its first cycle, so an EX time above 1 never finished.
* `mem.py`: `check_if_sd_committable` was never actually called (missing parentheses and a typo). It now requires the store to be at the ROB head. A clobbered loop variable was fixed.
* `wb.py`: a broadcast overwrote the RAT even when a younger instruction owned the register (WAW). It now updates only if the RAT still holds that tag.
* `issue.py`: two-digit registers (e.g. `F12`) were parsed wrongly in `Ld`/`Sd`.

Commit behaviour and the single CDB are unchanged, as in the handbook.

## 2. Tests

`python3 run_tests.py` runs every `tests/*.in` at issue widths 1–4 and compares the committed instruction stream, final registers and memory with a sequential reference interpreter. It also checks at most *width* issues per cycle, at most one WB per cycle, stage ordering, and in-order issue and commit.

| Test | What it covers |
|---|---|
| t1_spec_sample | The handbook example, edited so that it terminates |
| t2_independent_alu | Independent ops: benefit of wide issue |
| t3_dependency_chain | RAW chain: little benefit from width |
| t4_load_store_forwarding | Store-to-load forwarding and memory disambiguation |
| t5_branch_loop | Predictor learning a loop |
| t6_branch_not_taken_skip | Misprediction recovery |
| t7_structural_hazards | Few RS/FUs |
| t8_mixed_nested_loop | Everything together |

All 32 runs (8 tests × 4 widths) pass. In addition, 380 randomly generated programs (random units, ROB sizes, forward branches and a loop) were checked against the reference at all four widths with no failures.

## 3. Results

| Test | W1 cycles | W2 | W3 | W4 | last issue cycle (W1/W2/W3/W4) |
|---|---|---|---|---|---|
| t1 | 18 | 16 | 15 | 15 | 11 / 8 / 7 / 6 |
| t2 | 18 | 18 | 18 | 18 | 12 / 6 / 4 / 3 |
| t3 | 30 | 28 | 27 | 27 | 9 / 5 / 3 / 3 |
| t4 | 22 | 22 | 22 | 22 | 10 / 8 / 8 / 8 |
| t5 | 40 | 39 | 38 | 38 | 29 / 21 / 20 / 20 |
| t6 | 18 | 15 | 15 | 15 | 12 / 9 / 8 / 8 |
| t7 | 41 | 41 | 41 | 41 | 29 at all widths |
| t8 | 72 | 63 | 60 | 60 | 64 / 47 / 42 / 44 |

Wider issue clearly shortens the time to issue the program (last issue column). Total cycles improve less, and sometimes not at all (t2, t4, t7), because the machine keeps the handbook's single CDB and roughly one commit per cycle, so completion is commit-bound. Cases with branches (t1, t6, t8) gain more, since fetched instructions fill the time that misprediction penalties would otherwise waste. In t8 width 4 is slightly later than width 3 on last issue (44 vs 42) because extra wrong-path issue leads to more squashed work after mispredictions.

## 4. Limitations and interpretations

* The handbook sample would not terminate, so t1 was edited (`Addi R2,R2,-10`, branch offset fixed) to end.
* The original code used byte branch offsets; they are now instruction counts per the handbook (`PC + 1 + offset`).
* A store writes memory only when it is at the ROB head.
* There is one load/store unit, and only one branch recovery is handled per cycle.
* The report is Markdown, not PDF.
