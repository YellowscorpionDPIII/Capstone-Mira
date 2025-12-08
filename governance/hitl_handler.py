# governance/hitl_handler.py
"""
FastAPI Human-in-the-Loop approval service for Capstone-Mira governance.
Handles async approval/rejection with RBAC, audit logging, and Redis state.
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis
import jwt
from jwt.exceptions import PyJWTError
from governance.risk_assessor import RiskScore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# JWT settings
SECRET_KEY = "your-super-secret-jwt-key-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="Capstone-Mira HITL Service", version="1.0.0")

security = HTTPBearer()

class ApprovalRequest(BaseModel):
    workflow_id: str
    reviewer_notes: Optional[str] = None
    action: str  # "approve" or "reject"

class ApprovalResponse(BaseModel):
    status: str
    workflow_id: str
    timestamp: datetime
    reviewer_id: str

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT token verification with RBAC"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        reviewer_id: str = payload.get("sub")
        roles: list = payload.get("roles", [])
        
        if "hitl_reviewer" not in roles and "admin" not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return reviewer_id
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/approve/{workflow_id}", response_model=ApprovalResponse)
async def approve_workflow(
    workflow_id: str,
    req: ApprovalRequest,
    reviewer_id: str = Depends(verify_token)
):
    """Approve high-risk workflow with audit trail"""
    if req.action != "approve":
        raise HTTPException(status_code=400, detail="Use /reject endpoint for rejections")
    
    # Check Redis queue state
    task_id = redis_client.get(f"hitl:{workflow_id}")
    if not task_id:
        raise HTTPException(status_code=404, detail="No pending HITL request")
    
    try:
        # Update workflow status
        workflow_status = {
            "status": "approved",
            "approved_by": reviewer_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "notes": req.reviewer_notes,
            "risk_score": json.loads(redis_client.hget(f"risk:{workflow_id}", "score") or "{}")
        }
        
        redis_client.hset(f"workflow:{workflow_id}", mapping=workflow_status)
        redis_client.delete(f"hitl:{workflow_id}")
        redis_client.delete(f"risk:{workflow_id}")
        
        # Audit log
        audit_entry = {
            "event": "hitl_approved",
            "workflow_id": workflow_id,
            "reviewer": reviewer_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": req.reviewer_notes
        }
        redis_client.lpush("audit_log", json.dumps(audit_entry))
        
        logger.info(f"✅ HITL approved: {workflow_id} by {reviewer_id}")
        return ApprovalResponse(
            status="approved",
            workflow_id=workflow_id,
            timestamp=datetime.now(timezone.utc),
            reviewer_id=reviewer_id
        )
        
    except Exception as e:
        logger.error(f"❌ HITL approval failed: {e}")
        raise HTTPException(status_code=500, detail="Approval processing failed")

@app.post("/reject/{workflow_id}", response_model=ApprovalResponse)
async def reject_workflow(
    workflow_id: str,
    req: ApprovalRequest,
    reviewer_id: str = Depends(verify_token)
):
    """Reject workflow and trigger rollback"""
    if req.action != "reject":
        raise HTTPException(status_code=400, detail="Use /approve endpoint for approvals")
    
    try:
        # Rollback workflow
        redis_client.set(f"workflow:{workflow_id}:status", "rejected")
        
        # Audit log
        audit_entry = {
            "event": "hitl_rejected",
            "workflow_id": workflow_id,
            "reviewer": reviewer_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": req.reviewer_notes
        }
        redis_client.lpush("audit_log", json.dumps(audit_entry))
        
        logger.info(f"❌ HITL rejected: {workflow_id} by {reviewer_id}")
        return ApprovalResponse(
            status="rejected",
            workflow_id=workflow_id,
            timestamp=datetime.now(timezone.utc),
            reviewer_id=reviewer_id
        )
        
    except Exception as e:
        logger.error(f"❌ HITL rejection failed: {e}")
        raise HTTPException(status_code=500, detail="Rejection processing failed")

@app.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Check HITL status for workflow"""
    status = redis_client.hgetall(f"workflow:{workflow_id}")
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return dict(status)

@app.get("/pending")
async def get_pending_requests(reviewer_id: str = Depends(verify_token)):
    """List pending HITL requests for reviewer"""
    keys = redis_client.keys("hitl:*")
    pending = []
    for key in keys:
        workflow_id = key.decode().split(":")[1]
        risk_data = redis_client.hgetall(f"risk:{workflow_id}")
        pending.append({"workflow_id": workflow_id, "risk": risk_data})
    return pending

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
