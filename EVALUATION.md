# Evaluation

## Metrics & Coverage

The pipeline is evaluated against a diverse test suite broken down into multiple tiers of complexity:

- **Easy**: Basic arithmetic, if/else branching, and simple loops (`for`, `while`). These validate basic block routing.
- **Medium**: Arrays, nested branches/loops, and sequential function calls. These validate stack allocation (`alloca`) and pointer calculations (`getelementptr`).
- **Hard**: Structs, recursive functions, pointers, and floating-point logic. These stress memory bounds, phi-node generations (in optimized environments), and custom types.
- **Very Hard**: Function pointers, multi-dimensional arrays, nested structs, and pointer arithmetic. These ensure complete semantic robustness.

### Correctness Tracking
We evaluate two layers of correctness:
1. **Structural Validity**: Does `llvm-as` accept the generated output?
2. **Semantic Correctness**: When `lli` executes the IR, does the exit code match the mathematically expected value mapped in `secomd.py`? 

A typical run evaluates over 20 unique syntactical layouts. Passing the structural phase but failing the semantic phase highlights flaws in the compilation logic (though `clang -O0` is highly reliable).

## AI Repair Evaluation
The repair loop evaluates the ability of LLMs to correct corrupted IR strings based on compiler stderr output. The evaluation tracks:
- **Repair Status**: `REPAIRED` vs `UNREPAIRED`.
- **Attempts**: The pipeline allows up to 3 iterative repair attempts. A repair loop is considered successful if it can restore the structural validity of the IR (allowing `llvm-as` to succeed) without altering the core semantic intent.

### Example Repair Targets
- **SSA_VIOLATION**: Injecting multiple assignments to the same virtual register. LLMs generally perform well by renaming registers and cascading the updates.
- **MISSING_TERMINATOR**: Deleting block-ending `ret` instructions. LLMs must infer the expected return type and inject it.
- **TYPE_MISMATCH**: Misaligning `i32` pointers with `i64` stores. LLMs evaluate the struct/array layout and correct the cast.
