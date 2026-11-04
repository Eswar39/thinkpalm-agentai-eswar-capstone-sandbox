
import json
import os
import re
import time
from datetime import datetime
import gradio as gr

# ==========================================
# 1. MEMORY ENGINE (Short-term & Long-term)
# ==========================================
MEMORY_FILE = "taas_longterm_memory.json"

class MemoryEngine:
    def __init__(self):
        self.short_term_logs = []  # Current session buffer
        self.long_term_data = self._load_long_term()

    def _load_long_term(self):
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        return {"past_runs": [], "known_failure_patterns": {}}

    def save_long_term(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.long_term_data, f, indent=2)

    def log_short_term(self, entry):
        self.short_term_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {entry}")

    def store_test_run(self, run_id, suite_name, status, details):
        run_record = {
            "timestamp": datetime.now().isoformat(),
            "run_id": run_id,
            "suite": suite_name,
            "status": status,
            "details": details
        }
        self.long_term_data["past_runs"].append(run_record)
        
        # Track failure patterns in long-term memory
        if status == "FAILED":
            err_type = details.get("error_code", "UNKNOWN_ERR")
            self.long_term_data["known_failure_patterns"][err_type] = (
                self.long_term_data["known_failure_patterns"].get(err_type, 0) + 1
            )
        self.save_long_term()

    def get_memory_summary(self):
        runs = self.long_term_data["past_runs"]
        total = len(runs)
        passed = sum(1 for r in runs if r["status"] == "PASSED")
        failed = sum(1 for r in runs if r["status"] == "FAILED")
        patterns = self.long_term_data["known_failure_patterns"]
        return f"Total Past Runs: {total} | Passed: {passed} | Failed: {failed}\nFailure Frequency Patterns: {json.dumps(patterns)}"


# Initialize Memory Global
memory = MemoryEngine()


# ==========================================
# 2. CUSTOM TOOLS FOR AGENTS
# ==========================================
def log_parser_tool(raw_logs: str) -> dict:
    """Tool: Parses raw log text and extracts errors, status codes, and endpoints."""
    errors = re.findall(r'ERROR:\s*(.*)', raw_logs)
    status_codes = re.findall(r'HTTP\s*(\d{3})', raw_logs)
    return {
        "error_count": len(errors),
        "detected_errors": errors,
        "status_codes": status_codes
    }

def api_pinger_tool(endpoint_name: str) -> dict:
    """Tool: Simulates health check for CBU TAAS endpoints (SMS Gateway, Billing, Auth)."""
    endpoints = {
        "sms_gateway": {"status": "HEALTHY", "latency_ms": 45, "response_code": 200},
        "billing_api": {"status": "DEGRADED", "latency_ms": 1250, "response_code": 504},
        "auth_service": {"status": "HEALTHY", "latency_ms": 20, "response_code": 200}
    }
    return endpoints.get(endpoint_name.lower(), {"status": "UNKNOWN", "latency_ms": 0, "response_code": 404})

def test_runner_tool(suite_name: str) -> dict:
    """Tool: Simulates automated execution of test suites."""
    if suite_name == "CBU_SMS_Gateway_Suite":
        return {
            "suite": suite_name,
            "passed": 4,
            "failed": 1,
            "logs": "INFO: SMS payload generated.\nERROR: Gateway response timeout HTTP 504 on retry.\nINFO: Session closed.",
            "error_code": "ERR_GATEWAY_TIMEOUT"
        }
    else:
        return {
            "suite": suite_name,
            "passed": 5,
            "failed": 0,
            "logs": "INFO: All test cases executed successfully. HTTP 200 OK.",
            "error_code": None
        }


# ==========================================
# 3. AGENT 1: TEST-GENERATION & EXECUTION AGENT
# ==========================================
class TestGenerationAgent:
    def __init__(self, mem: MemoryEngine):
        self.mem = mem

    def generate_and_run(self, suite_name: str):
        self.mem.log_short_term(f"[Agent 1] Generating test case for: {suite_name}")
        
        # Tool Call: Run Test Suite
        result = test_runner_tool(suite_name)
        status = "FAILED" if result["failed"] > 0 else "PASSED"
        
        # Tool Call: Parse logs if failed
        parsed_log = {}
        if status == "FAILED":
            parsed_log = log_parser_tool(result["logs"])
            self.mem.log_short_term(f"[Agent 1] Test failed. Parsed {parsed_log['error_count']} errors.")
        else:
            self.mem.log_short_term(f"[Agent 1] Test completed successfully.")

        # Save to Long-term memory
        run_id = f"RUN-{int(time.time())}"
        self.mem.store_test_run(
            run_id=run_id,
            suite_name=suite_name,
            status=status,
            details={"error_code": result.get("error_code"), "parsed_log": parsed_log}
        )

        return status, result


# ==========================================
# 4. AGENT 2: COVERAGE-GAP & DIAGNOSTIC AGENT
# ==========================================
class CoverageGapAgent:
    def __init__(self, mem: MemoryEngine):
        self.mem = mem

    def analyze_gap_and_diagnose(self, latest_result: dict):
        self.mem.log_short_term("[Agent 2] Reviewing latest execution & historical memory...")
        
        suite = latest_result.get("suite")
        
        # Check System Ping Tool
        ping_res = api_pinger_tool("sms_gateway")
        
        # Query long term memory
        memory_summary = self.mem.get_memory_summary()
        known_failures = self.mem.long_term_data["known_failure_patterns"]
        
        analysis = []
        analysis.append("=== AGENT 2: DIAGNOSTIC & COVERAGE-GAP REPORT ===")
        analysis.append(f"Target Suite: {suite}")
        analysis.append(f"Live System Ping: {json.dumps(ping_res)}")
        analysis.append(f"Historical Memory: {memory_summary}")
        
        if latest_result.get("failed", 0) > 0:
            err = latest_result.get("error_code")
            freq = known_failures.get(err, 1)
            analysis.append(f"\n[!] DIAGNOSIS: Repeated failure pattern detected ({err} count: {freq}).")
            analysis.append("[+] RECOMMENDED COVERAGE FIX: Generate high-load async retry tests for SMS Gateway timeout.")
        else:
            analysis.append("\n[+] DIAGNOSIS: Execution healthy. No immediate coverage gaps identified.")
            
        return "\n".join(analysis)


# ==========================================
# 5. PIPELINE CONTROLLER & GRADIO UI
# ==========================================
gen_agent = TestGenerationAgent(memory)
gap_agent = CoverageGapAgent(memory)

def run_pipeline(suite_name):
    memory.log_short_term(f"Pipeline triggered for: {suite_name}")
    
    # Step 1: Agent 1 generates & runs test
    status, run_result = gen_agent.generate_and_run(suite_name)
    
    # Step 2: Agent 2 analyzes memory + results for coverage gaps
    diag_report = gap_agent.analyze_gap_and_diagnose(run_result)
    
    # Format outputs for UI
    short_term_str = "\n".join(memory.short_term_logs[-10:])
    long_term_str = memory.get_memory_summary()
    run_details_str = json.dumps(run_result, indent=2)
    
    return status, run_details_str, diag_report, short_term_str, long_term_str

# Build Gradio Interface
with gr.Blocks(title="CBU TAAS Multi-Agent Testing Pipeline") as demo:
    gr.Markdown("# 🤖 CBU TAAS — Full Agentic Testing Pipeline")
    gr.Markdown("Submitted for **Capstone Sandbox (QAD1223)** | **Evaluator:** aneesh.ks@thinkpalm.com")
    
    with gr.Row():
        suite_input = gr.Dropdown(
            choices=["CBU_SMS_Gateway_Suite", "CBU_Auth_Billing_Suite"],
            value="CBU_SMS_Gateway_Suite",
            label="Select CBU TAAS Test Suite"
        )
        btn = gr.Button("🚀 Run Multi-Agent Pipeline", variant="primary")
        
    with gr.Row():
        status_output = gr.Textbox(label="Execution Status", scale=1)
        
    with gr.Row():
        run_output = gr.Code(label="Agent 1: Execution & Log Parser Output", language="json")
        diag_output = gr.Textbox(label="Agent 2: Coverage Gap & Diagnostic Output", lines=8)
        
    with gr.Row():
        short_mem_output = gr.Textbox(label="Short-Term Memory (Session Trace)", lines=5)
        long_mem_output = gr.Textbox(label="Long-Term Memory (Persistent Failure Patterns)", lines=5)

    btn.click(
        fn=run_pipeline,
        inputs=[suite_input],
        outputs=[status_output, run_output, diag_output, short_mem_output, long_mem_output]
    )

if __name__ == "__main__":
    demo.launch(share=True, debug=True)
