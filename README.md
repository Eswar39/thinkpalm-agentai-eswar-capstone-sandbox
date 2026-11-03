# CBU TAAS — Full Agentic Testing Pipeline (Capstone Sandbox)

* **Developer:** Osuri Eswara Reddy (Eswar)
* **Track:** Agentic AI / AI Engineering
* **Lab Name:** Capstone Sandbox — Full Agent Pipeline (QAD1223)
* **Evaluator:** Aneesh K. S. (`aneesh.ks@thinkpalm.com`)

---

## 📌 Project Overview
This project delivers an end-to-end multi-agent testing pipeline tailored for CBU TAAS scenarios. It features short-term session tracing, long-term persistent memory for failure patterns, tool-calling capabilities, and an interactive Gradio web UI running directly in Google Colab.

### 🔑 Key Requirements Built:
1. **Memory Engine:** 
   - **Short-Term Memory:** In-memory session log trace.
   - **Long-Term Memory:** Persistent JSON storage (`taas_longterm_memory.json`) tracking overall pass/fail trends and failure frequency patterns (`ERR_GATEWAY_TIMEOUT`).
2. **Custom Tool-Calling:** 
   - `test_runner_tool`: Simulates CBU TAAS automated test execution.
   - `log_parser_tool`: Extracts error messages and HTTP status codes (e.g., HTTP 504) from raw logs.
   - `api_pinger_tool`: Checks endpoint health (SMS Gateway, Billing, Auth).
3. **Collaborating Agents:**
   - **Agent 1 (Test-Generation & Execution Agent):** Triggers test suites, parses execution logs, and records history.
   - **Agent 2 (Coverage-Gap & Diagnostic Agent):** Cross-references current execution with historical memory and active system state to detect coverage gaps and recommend regression tests.
4. **Interactive UI:** Built using Gradio for real-time demonstration and output log inspection.

---

## 🛠️ Tools & Technologies Used
* **Language:** Python 3.10+
* **Framework / UI:** Gradio
* **Execution Environment:** Google Colab / Local Python Environment
* **Data Storage:** JSON-based persistent file storage

---

## 🚀 How to Run

### Running in Google Colab
1. Open the notebook script in Google Colab.
2. Install dependencies: `!pip install gradio requests pydantic`
3. Run the pipeline script to launch the Gradio UI.
4. Access the generated public link (`https://xxxx.gradio.live`) to interact with the multi-agent pipeline.
