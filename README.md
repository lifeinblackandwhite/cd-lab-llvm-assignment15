# LLVM IR Generation and Validation Pipeline

## What This Is
This project is an automated pipeline that generates, validates, and runs LLVM Intermediate Representation (IR) from C code snippets using a Python orchestrator. It uses the LLVM toolchain (`clang`, `llvm-as`, `lli`) and features a semantic correctness checker and an AI-assisted failure analysis loop (powered by Anthropic's Claude API).

## Repository Structure
- `src/`: Core Python pipeline scripts (`main.py` and `secomd.py`).
- `testcases/`: Contains raw C and LLVM IR reference test files.
- `scripts`: (Provided as `./build.sh` and `./run.sh` in the root directory).
- `outputs/`: Automatically generated directory for LLVM IR outputs and test results.
- `DESIGN.md`: Architecture, approaches, and alternatives considered.
- `IMPLEMENTATION.md`: Specific technical details of the LLVM tools and python hooks.
- `EVALUATION.md`: Metrics, semantic tests, and evaluation outcomes.

## Prerequisites
- **Python 3.7+**
- **LLVM Toolchain**: `clang`, `llvm-as`, and `lli` must be installed.
- **Anthropic API Key**: Needed for failure analysis and the repair loop.

## How to Run

1. **Make Scripts Executable**
   Ensure the provided bash scripts have execute permissions:
   ```bash
   chmod +x build.sh run.sh serve_dashboard.sh
   ```

2. **Build the Environment**
   Run the build script to set up a virtual environment (`myvenv`) and install Python dependencies (e.g., `anthropic`):
   ```bash
   ./build.sh
   ```

3. **Set API Key**
   Export your Anthropic API key to enable the AI-powered semantic repair analysis:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ```

4. **Run the Automated Pipeline**
   Execute both the standard validation tests and the semantic repair loop using the run script:
   ```bash
   ./run.sh
   ```
   Check the `outputs/` directory for generated `.ll` files and the comprehensive `results.txt`.

5. **View the Dashboard (Interactive Code-to-IR)**
   You can view a rich web dashboard displaying test outcomes. It also features a real-time interactive compiler where you can paste C code and instantly view the generated LLVM IR!
   Start the local server:
   ```bash
   ./serve_dashboard.sh
   ```
   Then open `http://localhost:8000/dashboard/` in your browser to interact with the LLVM pipeline.
