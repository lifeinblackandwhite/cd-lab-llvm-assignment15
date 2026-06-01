# LLVM IR Generation and Validation Pipeline

This project is an automated pipeline that generates, validates, and runs LLVM Intermediate Representation (IR) from various C code snippets. It leverages the LLVM toolchain (`clang`, `llvm-as`, `lli`) through Python, and integrates with Anthropic's Claude API to automatically categorize and analyze validation failures.

## Project Structure

- `assignment15/`: Contains the core Python scripts.
  - `main.py`: The main testing pipeline that compiles C code, validates IR, and triggers AI analysis on failure.
  - `secomd.py`: Additional script (ensure to check its specific functionality).
- `myvenv/`: The recommended Python virtual environment location (ignored by git).
- `outputs/`: Directory where generated LLVM IR files, reference C files, and execution results are saved (ignored by git).

## Features

- **IR Generation**: Uses `clang` to compile C code into LLVM IR (`.ll`).
- **Validation**: Checks the validity of the generated IR using `llvm-as`.
- **Execution**: If the IR is valid, runs it directly using `lli`.
- **AI-Powered Failure Analysis**: When LLVM validation fails, the script queries the Claude API to classify the error (e.g., `SSA_VIOLATION`, `TYPE_ERROR`, etc.) and explains the reason.
- **Comprehensive Test Suite**: Contains tests ranging from basic arithmetic and loops to complex pointers and struct operations to stress-test the generation and validation flow.

## Prerequisites

- **Python 3.7+**
- **LLVM Toolchain**: Ensure `clang`, `llvm-as`, and `lli` are installed and available in your system's `PATH`.
- **Anthropic SDK**: Required for the failure analysis feature.

## Setup Instructions

1. **Activate the Virtual Environment:**
   ```bash
   source myvenv/bin/activate
   ```
   *(If `myvenv` doesn't exist, create it with `python -m venv myvenv`)*

2. **Install Dependencies:**
   Ensure the Anthropic Python SDK is installed in your environment:
   ```bash
   pip install anthropic
   ```

3. **Set Environment Variables:**
   The failure analysis requires an Anthropic API key to function:
   ```bash
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```

## Usage

To execute the pipeline and run all C tests:

```bash
cd assignment15
python main.py
```

### Outputs

After execution, check the `outputs/` folder or `assignment15/outputs/` for the generated files:
- `*.ll` generated LLVM IR files.
- `results.txt`: A detailed summary of tests that passed, failed, and the categorization of errors for failed tests.
