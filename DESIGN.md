# Design

## Approach
The core approach centers on using Python as an orchestration layer on top of standard LLVM command-line tools. This avoids the high barrier of entry required for writing C++ LLVM passes or integrating directly with the LLVM C++ API, while enabling rapid prototyping of tests. 

Key architectural components:
1. **Compilation (`clang`)**: C code is converted directly to unoptimized LLVM IR (`-O0`).
2. **Validation (`llvm-as`)**: The LLVM assembler validates the structural and typological correctness of the IR.
3. **Execution (`lli`)**: The LLVM interpreter runs the IR directly, allowing us to capture semantic exit codes without performing a full compilation to machine code.
4. **AI Integration Layer**: When an error occurs during validation (e.g., SSA violation), the raw error string and the broken IR are sent to a Large Language Model (Claude) to analyze the issue and attempt an autonomous repair.

## Alternatives Considered

1. **Direct C++ LLVM Passes**
   * *Description*: Writing native C++ tools linking against `libLLVM`.
   * *Why rejected*: Extremely verbose and difficult to iterate quickly on. Testing dynamic failure repairs using LLMs in a purely C++ environment is substantially more complex than string-manipulating Python scripts.
   
2. **llvmlite (Python Bindings)**
   * *Description*: Using the `llvmlite` library to programmatically generate IR in Python instead of using string literals and `clang`.
   * *Why rejected*: `llvmlite` is heavily tailored for Numba and sometimes lacks full support for modern LLVM IR paradigms needed for general-purpose C compilation equivalents. String-based orchestration provides a literal mapping to what the user would see when interacting with the tools directly.

3. **Static Analysis over Execution**
   * *Description*: Validating semantic correctness by parsing the IR tree rather than executing it.
   * *Why rejected*: Writing a robust static analyzer to catch semantic equivalence across pointers, nested loops, and function pointers is practically building a second compiler. Using `lli` to execute the IR and verify deterministic exit codes guarantees semantic correctness natively.
