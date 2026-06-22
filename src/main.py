import subprocess
import os
import tempfile
import anthropic

client = anthropic.Anthropic()

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
    result = subprocess.run(["lli", filename], capture_output=True, text=True)
    return result.returncode, result.stdout

def get_reference_ir(c_code: str, name: str) -> str:
    c_file = f"outputs/{name}_ref.c"
    ll_file = f"outputs/{name}_ref.ll"
    with open(c_file, "w") as f:
        f.write(c_code)
    subprocess.run(
        ["clang", "-S", "-emit-llvm", "-O0", c_file, "-o", ll_file],
        capture_output=True
    )
    with open(ll_file) as f:
        return f.read()

def analyze_failure(ir_code: str, error: str) -> str:
    """Ask Claude to categorize what kind of error occurred."""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""This LLVM IR failed validation. Categorize the failure.

Error:
{error}

IR:
{ir_code}

Reply in this exact format:
CATEGORY: (one of: SSA_VIOLATION, TYPE_ERROR, MISSING_TERMINATOR, INVALID_CONTROL_FLOW, UNDEFINED_VALUE, OTHER)
REASON: (one sentence explaining what went wrong)
FIXABLE: (YES or NO — can this be fixed with a simple repair)"""
            }]
        )
        return response.content[0].text
    except Exception as e:
        return f"CATEGORY: OTHER\nREASON: API Error: {e}\nFIXABLE: NO"


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
            print(f"Exit code: {exit_code}")
            return {
                "status": "PASS",
                "attempts": attempt + 1,
                "error_category": None,
                "error_detail": None
            }
        else:
            if attempt == 0:
                first_error = error   # save the original error
            print(f"❌ Invalid")
            if attempt < max_retries - 1:
                ir = repair_ir(ir, error)
            else:
                # Analyze the failure
                print("🔍 Analyzing failure...")
                analysis = analyze_failure(ir, first_error)
                print(analysis)
                return {
                    "status": "FAIL",
                    "attempts": attempt + 1,
                    "error_category": analysis,
                    "error_detail": first_error
                }

    return {"status": "FAIL", "attempts": max_retries,
            "error_category": "UNKNOWN", "error_detail": "Max retries exceeded"}


# ── test cases ─────────────────────────────────────────

tests = {

    # ── EASY (should pass) ──────────────────────────────

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

    # ── MEDIUM (may struggle) ───────────────────────────

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

    # ── HARD (likely to fail) ───────────────────────────

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
# ── VERY HARD (designed to break) ──────────────────

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
struct Inner {
    int x;
    int y;
};
struct Outer {
    struct Inner p;
    int z;
};
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
struct Point {
    int x;
    int y;
};
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
    int arr[5] = {10, 20, 30, 40, 50};
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
    matrix[0][0] = 1;
    matrix[0][1] = 2;
    matrix[1][0] = 3;
    matrix[1][1] = 4;
    return matrix[0][0] + matrix[1][1];
}
""",
}

# ── run everything ─────────────────────────────────────

os.makedirs("outputs", exist_ok=True)

results = {}
for name, code in tests.items():
    result = pipeline(name, code)
    results[name] = result

# summary
print(f"\n{'='*50}")
print("SUMMARY")
print(f"{'='*50}")

passed = [n for n, r in results.items() if r["status"] == "PASS"]
failed = [n for n, r in results.items() if r["status"] == "FAIL"]

for name, r in results.items():
    status = "✅ PASS" if r["status"] == "PASS" else "❌ FAIL"
    print(f"{status}  {name:25s}  attempts: {r['attempts']}")

print(f"\nPassed: {len(passed)}/{len(results)}")
print(f"Failed: {len(failed)}/{len(results)}")

# ── failure breakdown ──────────────────────────────────

if failed:
    print(f"\n{'='*50}")
    print("FAILURE ANALYSIS")
    print(f"{'='*50}")
    for name in failed:
        print(f"\n[ {name} ]")
        print(results[name]["error_category"])

# ── save results to file ───────────────────────────────

with open("outputs/results.txt", "w") as f:
    f.write("ASSIGNMENT 15 — RESULTS\n\n")
    for name, r in results.items():
        f.write(f"{name}: {r['status']} (attempts: {r['attempts']})\n")
        if r["status"] == "FAIL":
            f.write(f"  {r['error_category']}\n")

import json
with open("outputs/main_results.json", "w") as f:
    json.dump({"tests": results, "summary": {"passed": len(passed), "failed": len(failed), "total": len(results)}}, f, indent=4)

print("\n📄 Results saved to outputs/results.txt and outputs/main_results.json")