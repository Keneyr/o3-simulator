Tomasulo Algorithm Simulation
* includes instructions of int_add, fp_add, fp_multi, load, store, branch;
* implements ROB, RAT, load-store-queue;
* implements out-of-order processing and memory disambiguation; 
* implements in-order multi-issue (issue width 1-4, default 1);
* implements a 1-bit branch predictor with an 8-entry BTB and misprediction recovery.

How to run:
```
cd code
python3 main.py [input_file]      # default input: test_case.txt
```
The issue width is set inside the input file with the line `Issue width = N`.
Branch offsets (`Beq/Bne Rs, Rt, offset`) are counted in instructions: target = PC + 1 + offset.

Tests:
```
python3 run_tests.py        # runs tests/*.in at issue widths 1-4 and checks them against a sequential reference
python3 run_tests.py -v     # also prints the simulator output
```
See REPORT.md for what was changed and the results.
