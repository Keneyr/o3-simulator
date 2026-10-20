#!/usr/bin/env python3
"""Run every tests/*.in with issue widths 1-4 through code/main.py and check
  * the committed instruction stream, final registers and memory against a plain sequential interpreter
  * at most <width> instructions are issued per cycle, one WB (CDB) per cycle, stages are in order

Usage: python3 run_tests.py [-v]     (-v also prints the simulator output)
"""
import glob
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.join(HERE, 'code')
sys.path.insert(0, CODE)
from init import read_input  # noqa: E402


def reference(path):
    """Sequential execution: returns (executed instruction texts, R regs, F regs, memory)."""
    cfg, ins = read_input(path)
    r, f, mem = list(cfg['reg_int']), list(cfg['reg_fp']), list(cfg['memory'])
    pc, trace = 0, []
    while 0 <= pc < len(ins):
        if len(trace) > 20000:
            raise RuntimeError('reference: program does not terminate')
        text = ins[pc]
        trace.append(text)
        op, *a = text.split(' ')
        pc += 1
        if op in ('Add', 'Sub'):
            r[int(a[0][1:])] = r[int(a[1][1:])] + (1 if op == 'Add' else -1) * r[int(a[2][1:])]
        elif op == 'Addi':
            r[int(a[0][1:])] = r[int(a[1][1:])] + int(a[2])
        elif op in ('Add.d', 'Sub.d', 'Mult.d'):
            x, y = f[int(a[1][1:])], f[int(a[2][1:])]
            f[int(a[0][1:])] = x + y if op == 'Add.d' else x - y if op == 'Sub.d' else x * y
        elif op in ('Ld', 'Sd'):
            m = re.fullmatch(r'(-?\d+)\(R(\d+)\)', a[1])
            addr = int(m.group(1)) + r[int(m.group(2))]
            if op == 'Ld':
                f[int(a[0][1:])] = mem[addr]
            else:
                mem[addr] = f[int(a[0][1:])]
        else:
            equal = r[int(a[0][1:])] == r[int(a[1][1:])]
            if equal == (op == 'Beq'):
                pc += int(a[2])
        r[0] = 0
    return trace, r, f, mem


def simulate(text, width):
    with tempfile.NamedTemporaryFile('w', suffix='.in', delete=False) as t:
        t.write(re.sub(r'(?im)^\s*issue width\s*=.*$', '', text) + '\nIssue width = %d\n' % width)
    try:
        p = subprocess.run([sys.executable, 'main.py', t.name], cwd=CODE, capture_output=True,
                           text=True, timeout=120)
    finally:
        os.unlink(t.name)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout


def parse_output(out):
    lines = out.splitlines()
    rows = []
    for line in lines[1:]:
        if not line.strip():
            break
        lists = [[int(x) for x in g.split(',') if x.strip()] for g in re.findall(r'\[([^\]]*)\]', line)]
        rows.append((line[:30].strip(), *lists))   # text, issue, exe, mem, wb, commit
    vals = [l[7:].split() for l in lines if l.startswith('value:')]
    regs_r = [int(x) for x in vals[0]]
    regs_f = [float(x) for x in vals[1]]
    mem = {}
    start = lines.index('NON-ZERO MEMORY VALUES') + 2
    for l in lines[start:]:
        if l.strip():
            a, v = l.split()
            mem[int(a)] = float(v)
    return rows, regs_r, regs_f, mem


def check(path, text, width, out, ref):
    trace, r, f, mem = ref
    rows, regs_r, regs_f, got_mem = parse_output(out)
    problems = []
    if [x[0] for x in rows] != trace:
        problems.append('committed instruction stream differs from sequential execution')
    if regs_r != r or regs_f != f:
        problems.append('registers differ')
    if got_mem != {a: v for a, v in enumerate(mem) if v != 0}:
        problems.append('memory differs')
    issues = Counter(x[1][0] for x in rows if x[1])
    wbs = Counter(x[4][0] for x in rows if x[4])
    if any(n > width for n in issues.values()):
        problems.append('more than %d issues in one cycle' % width)
    if any(n > 1 for n in wbs.values()):
        problems.append('more than one WB in one cycle (one CDB)')
    for text_, iss, exe, mm, wb, com in rows:
        if not (iss and len(exe) == 2 and com and iss[0] < exe[0] <= exe[1]):
            problems.append('bad stage order: ' + text_)
            break
        if wb and not (wb[0] > exe[1] and com[0] > wb[0]):
            problems.append('bad WB/COMMIT order: ' + text_)
            break
        if not wb and not com[0] > exe[1] and not text_.startswith('Sd'):
            problems.append('bad COMMIT order: ' + text_)
            break
    if any(a[1][0] > b[1][0] or a[5][0] > b[5][0] for a, b in zip(rows, rows[1:])):
        problems.append('issue/commit not in program order')
    cycles = max((x[5][0] for x in rows), default=0)
    return problems, cycles, len(rows), max((x[1][0] for x in rows), default=0)


def main():
    verbose = '-v' in sys.argv
    failures = 0
    print('%-30s %-6s %8s %8s %6s %10s  %s' % ('test', 'width', 'cycles', 'commits', 'IPC', 'last issue', 'result'))
    for path in sorted(glob.glob(os.path.join(HERE, 'tests', '*.in'))):
        text = open(path).read()
        ref = reference(path)
        for width in (1, 2, 3, 4):
            out = simulate(text, width)
            problems, cycles, n, last_issue = check(path, text, width, out, ref)
            failures += bool(problems)
            print('%-30s %-6d %8d %8d %6.3f %10d  %s' % (os.path.basename(path), width, cycles, n,
                                                       n / cycles if cycles else 0, last_issue,
                                                       'PASS' if not problems else 'FAIL'))
            for p in problems:
                print('    ' + p)
            if verbose or problems:
                print(out)
    print('\n%d failure(s)' % failures)
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
