# Demo Test Cases

These test cases are designed to be used during your demonstration. You can paste the C code snippets into the "Live IR Generator" on the web dashboard, or save them as `.c` files in the `testcases/` directory to run them via the command-line pipeline.

## Test Case 1: Simple Return (Baseline)
**Goal:** Demonstrate the basic functionality of the C to LLVM IR pipeline, structural validation, and semantic execution.

**C Code:**
```c
int main() {
    return 42;
}
```
**Expected Outcome:**
- Valid compilation using `clang`.
- LLVM IR is generated cleanly without errors.
- `lli` execution exit code should correctly be `42`.

---

## Test Case 2: Conditional Logic (Control Flow)
**Goal:** Show how the pipeline handles branching (`br` instructions in LLVM IR) and memory allocation (`alloca`).

**C Code:**
```c
int main() {
    int a = 10;
    int b = 20;
    if (a < b) {
        return 1;
    } else {
        return 0;
    }
}
```
**Expected Outcome:**
- Execution exit code should be `1`.
- The generated LLVM IR will contain multiple basic blocks corresponding to the `if` and `else` branches.

---

## Test Case 3: Loops and Arithmetic
**Goal:** Demonstrate loop handling (`br`, `icmp`) and basic arithmetic operations in LLVM IR.

**C Code:**
```c
int main() {
    int sum = 0;
    for (int i = 0; i < 5; i++) {
        sum += i; // 0+1+2+3+4 = 10
    }
    return sum;
}
```
**Expected Outcome:**
- Execution exit code should be `10`.
- The IR will show loop back-edges, incrementing logic, and conditional branching to exit the loop.

---

## Test Case 4: AI Repair Demonstration (Intentional IR Error)
**Goal:** Showcase the Anthropic Claude AI repair loop catching and fixing a structural issue.
*Note: This can be demonstrated if your pipeline runs on pre-existing `.ll` files in the `testcases/` directory.*

**Broken LLVM IR (Save as `testcases/broken.ll`):**
```llvm
define i32 @main() {
entry:
  %retval = alloca i32, align 4
  store i32 0, i32* %retval, align 4
  ; Error: Missing terminator (return) instruction!
}
```
**Expected Outcome:**
- `llvm-as` will fail to validate due to a missing terminator instruction in the `entry` block.
- The pipeline will detect the failure and send the broken IR along with the `llvm-as` error log to Anthropic Claude.
- The AI will categorize the error and attempt to autonomously fix it by appending `ret i32 0`.
- The repaired IR will be re-validated and executed.
