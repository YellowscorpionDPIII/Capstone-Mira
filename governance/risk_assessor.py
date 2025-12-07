# 1. Create directory structure
mkdir -p governance orchestrator tests/governance

# 2. Create files with provided code (copy-paste from previous response)
touch governance/risk_assessor.py
touch governance/hitl_handler.py
touch orchestrator/governance_middleware.py
touch tests/test_governance.py
touch config/governance.yaml

# 3. Edit files (use VS Code or nano)
code governance/risk_assessor.py  # Paste RiskAssessor class
code governance/hitl_handler.py   # Paste FastAPI app
code orchestrator/governance_middleware.py  # Paste middleware
