# Implementation Details

## LLVM Toolchain Orchestration

The pipeline is entirely wrapped in Python's `subprocess` module, which handles temporal file generation and process execution. 

### Generation (`clang`)
To produce pure IR, we invoke Clang with the following arguments:
```bash
clang -emit-llvm -S -O0 temp.c -o temp.ll
```
- `-emit-llvm -S`: Tells the compiler to output human-readable LLVM IR instead of object code or machine code.
- `-O0`: Disables optimizations. This is crucial as `-O2` or `-O3` might completely fold constants and remove the actual IR logic we are attempting to validate, simplifying the test case into a single return literal.

### Validation (`llvm-as`)
We pipe the generated `.ll` files to `llvm-as`:
```bash
llvm-as file.ll
```
`llvm-as` acts as an assembler, strictly verifying the semantic and syntactical rules of LLVM IR (like SSA form, strong typing, and basic block termination). Non-zero exit codes immediately flag the IR as invalid, allowing the pipeline to capture `stderr` for analysis.

### Execution (`lli`)
For valid IR, we execute it using the LLVM interpreter:
```bash
lli file.ll
```
The exit code (simulating a C `return` statement from `main`) is captured and compared against the expected output mapping to ensure semantic correctness.

## Error Injection & AI Repair Loop
The `secomd.py` script implements a targeted failure mode injection:
1. **Mutation**: Valid IR is forcefully mutated.
   - *SSA Violation*: An `alloca` instruction is duplicated.
   - *Missing Terminator*: `ret` instructions are stripped from a basic block.
   - *Type Mismatch*: Specifically altering target types (e.g., swapping `i32` for `i64`).
2. **Analysis/Repair**: The mutated IR fails `llvm-as`. The pipeline takes the `llvm-as` stderr payload alongside the broken IR and prompts an Anthropic Claude model to autonomously resolve the structural fault. If the LLM returns valid IR, the test is marked `REPAIRED`.
