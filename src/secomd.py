import subprocess
import os
import tempfile
import anthropic

client = anthropic.Anthropic()

# ── expected outputs ───────────────────────────────────

expected_outputs = {
    "arithmetic":         43,
    "if_else":            1,
    "for_loop":           45,
    "while_loop":         128,
    "function_call":      7,
    "array":              30,
    "nested_if":          2,
    "nested_loop":        9,
    "multiple_functions": 27,
    "pointer":            100,
    "struct":             7,
    "recursive":          120,
    "float_ops":          6,
    "function_pointer":   20,
    "nested_struct":      6,
    "global_variable":    3,
    "switch_statement":   20,
    "array_of_structs":   10,
    "pointer_arithmetic": 30,
    "multiple_pointers":  10,
    "ternary_nested":     7,
    "string_length":      5,
    "multiarray_2d":      5,
}

# ── functions ──────────────────────────────────────────

def generate_ir(c_code: str) -> str:
    # Use clang to generate LLVM IR directly
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(c_code)
        temp_c_file = f.name
    
    temp_ll_file = temp_c_file.replace('.c', '.ll')
    
    try:
        result = subprocess.run(
            ["clang", "-emit-llvm", "-S", "-O0", temp_c_file, "-o", temp_ll_file],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Clang error: {result.stderr}")
        
        with open(temp_ll_file, 'r') as f:
            return f.read()
    finally:
        if os.path.exists(temp_c_file):
            os.remove(temp_c_file)
        if os.path.exists(temp_ll_file):
            os.remove(temp_ll_file)


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def repair_ir(ir_code: str, error: str) -> str:
    print("🔧 Attempting repair...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""This LLVM IR has an error. Fix it.

Error from llvm-as:
{error}

Broken IR:
{ir_code}

Output ONLY the fixed LLVM IR, nothing else."""
            }]
        )
        return strip_code_fences(response.content[0].text)
    except Exception as e:
        print(f"⚠️ API Error during repair: {e}")
        return ir_code

def analyze_failure(ir_code: str, error: str) -> str:
    return "UNKNOWN"


def validate_ir(ir_code: str, filename: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(ir_code)
    result = subprocess.run(
        ["llvm-as", filename],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stderr


def run_ir(filename: str):
    result = subprocess.run(
        ["lli", filename],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout


def inject_error(ir_code: str, error_type: str) -> str:
    lines = ir_code.split('\n')

    if error_type == "ssa_violation":
        # Insert a duplicate definition to break SSA
        for i, line in enumerate(lines):
            if '= alloca i32' in line:
                lines.insert(i + 1, line)  # duplicate alloca
                break

    elif error_type == "missing_terminator":
        # Remove ALL ret instructions so block has no terminator
        lines = [line for line in lines if not line.strip().startswith('ret ')]

    elif error_type == "type_mismatch":
        # Change one i32 to i64 to cause type mismatch
        for i, line in enumerate(lines):
            if 'store i32' in line:
                lines[i] = line.replace('store i32', 'store i64', 1)
                break

    return '\n'.join(lines)


def repair_pipeline(name: str, ir_code: str, error_type: str):
    print(f"\n{'='*50}")
    print(f"REPAIR TEST: {name} — injecting {error_type}")
    print(f"{'='*50}")

    broken_ir = inject_error(ir_code, error_type)
    filename = f"outputs/repair_{name}_{error_type}.ll"
    current_ir = broken_ir

    for attempt in range(3):
        valid, error = validate_ir(current_ir, filename)
        if valid:
            print(f"✅ Repaired after {attempt} fix(es)!")
            return {"status": "REPAIRED", "attempts": attempt}
        else:
            print(f"Attempt {attempt + 1}: broken — repairing...")
            current_ir = repair_ir(current_ir, error)

    print("❌ Could not repair")
    return {"status": "UNREPAIRED", "attempts": 3}


def pipeline(name: str, c_code: str, max_retries=3):
    print(f"\n{'='*50}")
    print(f"TEST: {name}")
    print(f"{'='*50}")

    filename = f"outputs/{name}.ll"
    ir = generate_ir(c_code)
    first_error = None

    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1}...")
        valid, error = validate_ir(ir, filename)

        if valid:
            print("✅ Valid IR!")
            exit_code, output = run_ir(filename)

            expected = expected_outputs.get(name)
            if expected is not None:
                if exit_code == expected:
                    print(f"✅ Correct output! (got {exit_code}, expected {expected})")
                    semantic = "CORRECT"
                else:
                    print(f"❌ Wrong output! (got {exit_code}, expected {expected})")
                    semantic = "WRONG"
            else:
                semantic = "UNKNOWN"

            return {
                "status": "PASS",
                "attempts": attempt + 1,
                "exit_code": exit_code,
                "semantic": semantic
            }
        else:
            if attempt == 0:
                first_error = error
            print(f"❌ Invalid IR")
            if attempt < max_retries - 1:
                ir = repair_ir(ir, error)
            else:
                print("🔍 Analyzing failure...")
                analysis = analyze_failure(ir, first_error)
                print(analysis)
                return {
                    "status": "FAIL",
                    "attempts": attempt + 1,
                    "exit_code": None,
                    "semantic": "FAIL",
                    "error_category": analysis,
                    "error_detail": first_error
                }

    return {
        "status": "FAIL",
        "attempts": max_retries,
        "exit_code": None,
        "semantic": "FAIL"
    }


# ── test cases ─────────────────────────────────────────

tests = {

    "arithmetic": """
int main() {
    int a = 10;
    int b = 3;
    int c = a + b;
    int d = a * b;
    return c + d;
}
""",

    "if_else": """
int main() {
    int x = 10;
    if (x > 5) {
        return 1;
    } else {
        return 0;
    }
}
""",

    "for_loop": """
int main() {
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        sum = sum + i;
    }
    return sum;
}
""",

    "while_loop": """
int main() {
    int x = 1;
    while (x < 100) {
        x = x * 2;
    }
    return x;
}
""",

    "function_call": """
int add(int a, int b) {
    return a + b;
}
int main() {
    int result = add(3, 4);
    return result;
}
""",

    "array": """
int main() {
    int arr[5];
    arr[0] = 10;
    arr[1] = 20;
    return arr[0] + arr[1];
}
""",

    "nested_if": """
int main() {
    int x = 10;
    int y = 20;
    if (x > 5) {
        if (y > 15) {
            return 2;
        } else {
            return 1;
        }
    }
    return 0;
}
""",

    "nested_loop": """
int main() {
    int sum = 0;
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            sum = sum + 1;
        }
    }
    return sum;
}
""",

    "multiple_functions": """
int square(int x) {
    return x * x;
}
int cube(int x) {
    return x * square(x);
}
int main() {
    return cube(3);
}
""",

    "pointer": """
int main() {
    int x = 42;
    int *p = &x;
    *p = 100;
    return x;
}
""",

    "struct": """
struct Point {
    int x;
    int y;
};
int main() {
    struct Point p;
    p.x = 3;
    p.y = 4;
    return p.x + p.y;
}
""",

    "recursive": """
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
int main() {
    return factorial(5);
}
""",

    "float_ops": """
int main() {
    float a = 3.14;
    float b = 2.0;
    float c = a * b;
    return (int)c;
}
""",

    "function_pointer": """
int add(int a, int b) { return a + b; }
int sub(int a, int b) { return a - b; }
int main() {
    int (*op)(int, int) = add;
    int result = op(10, 3);
    op = sub;
    result = result + op(10, 3);
    return result;
}
""",

    "nested_struct": """
struct Inner { int x; int y; };
struct Outer { struct Inner p; int z; };
int main() {
    struct Outer o;
    o.p.x = 1;
    o.p.y = 2;
    o.z = 3;
    return o.p.x + o.p.y + o.z;
}
""",

    "global_variable": """
int counter = 0;
void increment() {
    counter = counter + 1;
}
int main() {
    increment();
    increment();
    increment();
    return counter;
}
""",

    "switch_statement": """
int main() {
    int x = 2;
    int result = 0;
    switch(x) {
        case 1: result = 10; break;
        case 2: result = 20; break;
        case 3: result = 30; break;
        default: result = 99;
    }
    return result;
}
""",

    "array_of_structs": """
struct Point { int x; int y; };
int main() {
    struct Point pts[3];
    pts[0].x = 1; pts[0].y = 2;
    pts[1].x = 3; pts[1].y = 4;
    pts[2].x = 5; pts[2].y = 6;
    return pts[0].x + pts[1].y + pts[2].x;
}
""",

    "pointer_arithmetic": """
int main() {
    int arr[5];
    arr[0] = 10; arr[1] = 20; arr[2] = 30;
    arr[3] = 40; arr[4] = 50;
    int *p = arr;
    p = p + 2;
    return *p;
}
""",

    "multiple_pointers": """
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}
int main() {
    int x = 5;
    int y = 10;
    swap(&x, &y);
    return x;
}
""",

    "ternary_nested": """
int max3(int a, int b, int c) {
    return a > b ? (a > c ? a : c) : (b > c ? b : c);
}
int main() {
    return max3(3, 7, 5);
}
""",

    "string_length": """
int strlen_custom(char *s) {
    int len = 0;
    while (s[len] != '\\0') {
        len++;
    }
    return len;
}
int main() {
    char str[] = "hello";
    return strlen_custom(str);
}
""",

    "multiarray_2d": """
int main() {
    int matrix[2][2];
    matrix[0][0] = 1; matrix[0][1] = 2;
    matrix[1][0] = 3; matrix[1][1] = 4;
    return matrix[0][0] + matrix[1][1];
}
"""
}


# ── run all tests ──────────────────────────────────────

os.makedirs("outputs", exist_ok=True)

results = {}
for name, code in tests.items():
    results[name] = pipeline(name, code)

# ── main summary ───────────────────────────────────────

passed  = [n for n, r in results.items() if r["status"] == "PASS"]
failed  = [n for n, r in results.items() if r["status"] == "FAIL"]

print(f"\n{'='*50}")
print("SUMMARY")
print(f"{'='*50}")
for name, r in results.items():
    status = "✅ PASS" if r["status"] == "PASS" else "❌ FAIL"
    print(f"{status}  {name:25s}  attempts: {r['attempts']}")

print(f"\nPassed: {len(passed)}/{len(results)}")
print(f"Failed: {len(failed)}/{len(results)}")

# ── semantic correctness ───────────────────────────────

print(f"\n{'='*50}")
print("SEMANTIC CORRECTNESS")
print(f"{'='*50}")
correct = 0
wrong   = 0
for name, r in results.items():
    if r["status"] == "PASS":
        sem      = r.get("semantic", "UNKNOWN")
        expected = expected_outputs.get(name, "?")
        got      = r.get("exit_code", "?")
        mark     = "✅" if sem == "CORRECT" else "❌"
        if sem == "CORRECT":
            correct += 1
        else:
            wrong += 1
        print(f"{mark}  {name:25s}  got: {str(got):4}  expected: {expected}")

print(f"\nSemantically correct: {correct}/{correct + wrong}")

# ── failure breakdown ──────────────────────────────────

if failed:
    print(f"\n{'='*50}")
    print("FAILURE ANALYSIS")
    print(f"{'='*50}")
    for name in failed:
        print(f"\n[ {name} ]")
        print(results[name].get("error_category", "No analysis available"))

# ── repair loop tests ──────────────────────────────────

print(f"\n{'='*50}")
print("REPAIR LOOP TESTS")
print(f"{'='*50}")

base_c = """
int main() {
    int a = 10;
    int b = 20;
    int c = a + b;
    return c;
}
"""
base_ir = generate_ir(base_c)

error_types    = ["ssa_violation", "missing_terminator", "type_mismatch"]
repair_results = {}
for error_type in error_types:
    repair_results[error_type] = repair_pipeline("base", base_ir, error_type)

print(f"\n{'='*50}")
print("REPAIR SUMMARY")
print(f"{'='*50}")
for error_type, r in repair_results.items():
    status = "✅ REPAIRED" if r["status"] == "REPAIRED" else "❌ FAILED"
    print(f"{status}  {error_type:25s}  attempts: {r['attempts']}")

# ── save full results ──────────────────────────────────

with open("outputs/results.txt", "w") as f:
    f.write("ASSIGNMENT 15 — FULL RESULTS\n\n")

    f.write("=== TEST CASES ===\n")
    for name, r in results.items():
        f.write(f"{name}: {r['status']} | attempts: {r['attempts']} | "
                f"exit_code: {r.get('exit_code','N/A')} | "
                f"semantic: {r.get('semantic','N/A')}\n")

    f.write(f"\nPassed: {len(passed)}/{len(results)}\n")
    f.write(f"Semantically correct: {correct}/{correct + wrong}\n")

    f.write("\n=== REPAIR LOOP ===\n")
    for error_type, r in repair_results.items():
        f.write(f"{error_type}: {r['status']} | attempts: {r['attempts']}\n")

import json
with open("outputs/secomd_results.json", "w") as f:
    json.dump({
        "tests": results,
        "repair_results": repair_results,
        "summary": {
            "passed": len(passed),
            "failed": len(failed),
            "total": len(results),
            "semantically_correct": correct,
            "semantically_wrong": wrong
        }
    }, f, indent=4)

print("\n📄 Results saved to outputs/results.txt and outputs/secomd_results.json")