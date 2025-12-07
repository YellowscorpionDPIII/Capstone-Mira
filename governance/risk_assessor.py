"""
Risk Assessment Engine for Capstone-Mira workflows.

This module provides risk scoring and Human-in-the-Loop (HITL) orchestration
for workflow governance.
"""

import logging
import json
import yaml
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RiskScore:
    """
    Data class representing the results of a risk assessment.
    
    Attributes:
        workflow_id: Unique identifier for the workflow
        financial_risk: Financial risk score (0-1)
        compliance_risk: Compliance risk score (0-1)
        explainability_risk: Explainability risk score (0-1)
        composite_score: Overall composite risk score (0-1)
        requires_hitl: Whether Human-in-the-Loop review is required
        timestamp: When the assessment was performed
        details: Additional context about the risk assessment
    """
    workflow_id: str
    financial_risk: float
    compliance_risk: float
    explainability_risk: float
    composite_score: float
    requires_hitl: bool
    timestamp: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert RiskScore to dictionary."""
        return asdict(self)


class RiskAssessor:
    """
    Risk assessment engine for Capstone-Mira workflows.
    
    This class evaluates workflows based on financial, compliance, and
    explainability criteria. It caches results in Redis and queues
    Human-in-the-Loop reviews via Celery when risk thresholds are exceeded.
    """
    
    def __init__(self, config_path: Optional[str] = None, redis_client=None, celery_app=None):
        """
        Initialize the RiskAssessor.
        
        Args:
            config_path: Path to configuration YAML file
            redis_client: Redis client instance (optional, for testing)
            celery_app: Celery application instance (optional, for testing)
        """
        self.config = self._load_config(config_path)
        self.thresholds = self.config.get('risk_thresholds', self._get_default_config()['risk_thresholds'])
        
        # Initialize Redis client
        if redis_client is not None:
            self.redis_client = redis_client
        else:
            try:
                import redis
                redis_config = self.config.get('redis', {})
                self.redis_client = redis.Redis(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0),
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis connection established")
            except Exception as e:
                logger.warning(f"⚠️ Redis not available: {e}. Running without caching.")
                self.redis_client = None
        
        # Initialize Celery app
        if celery_app is not None:
            self.celery_app = celery_app
        else:
            try:
                from celery import Celery
                celery_config = self.config.get('celery', {})
                self.celery_app = Celery(
                    'mira_governance',
                    broker=celery_config.get('broker_url', 'redis://localhost:6379/0'),
                    backend=celery_config.get('result_backend', 'redis://localhost:6379/0')
                )
                logger.info("✅ Celery app initialized")
            except Exception as e:
                logger.warning(f"⚠️ Celery not available: {e}. Running without async tasks.")
                self.celery_app = None
        
        logger.info(f"RiskAssessor initialized with thresholds: {self.thresholds}")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            # Try default location
            import os
            default_paths = [
                'config/governance.yaml',
                '/home/runner/work/Capstone-Mira/Capstone-Mira/config/governance.yaml',
                os.path.join(os.path.dirname(__file__), '..', 'config', 'governance.yaml')
            ]
            
            for path in default_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded configuration from {config_path}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        logger.info("Using default configuration")
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Returns:
            Default configuration dictionary
        """
        return {
            'risk_thresholds': {
                'financial': 10000,  # USD threshold for high risk
                'compliance': 0.8,   # Compliance score (0-1)
                'explainability': 0.7,  # AI explainability threshold (0-1)
                'total': 0.75        # Composite risk score threshold
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'celery': {
                'broker_url': 'redis://localhost:6379/0',
                'result_backend': 'redis://localhost:6379/0'
            },
            'hitl': {
                'timeout_seconds': 86400  # 24 hours
            }
        }
    
    def assess_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> RiskScore:
        """
        Assess risk for a workflow and trigger HITL if needed.
        
        Args:
            workflow_id: Unique identifier for the workflow
            workflow_data: Workflow information containing:
                - financial_amount: Transaction/budget amount in USD
                - compliance_data: Dict with compliance information
                - ai_model_type: Type of AI model used (if applicable)
                - explainability_score: Existing explainability score (0-1)
                
        Returns:
            RiskScore object with assessment results
        """
        logger.info(f"Assessing workflow: {workflow_id}")
        
        # Calculate individual risk scores
        financial_risk = self._calc_financial_risk(workflow_data)
        compliance_risk = self._check_compliance(workflow_data)
        explainability_risk = self._assess_explainability(workflow_data)
        
        # Calculate composite score (weighted average)
        composite_score = (
            financial_risk * 0.4 +
            compliance_risk * 0.35 +
            explainability_risk * 0.25
        )
        
        # Determine if HITL is required
        # Check if financial amount exceeds threshold (in dollars)
        financial_threshold_exceeded = workflow_data.get('financial_amount', 0) > self.thresholds['financial']
        
        requires_hitl = (
            financial_threshold_exceeded or
            compliance_risk > self.thresholds['compliance'] or
            explainability_risk > self.thresholds['explainability'] or
            composite_score > self.thresholds['total']
        )
        
        # Create risk score object
        risk_score = RiskScore(
            workflow_id=workflow_id,
            financial_risk=financial_risk,
            compliance_risk=compliance_risk,
            explainability_risk=explainability_risk,
            composite_score=composite_score,
            requires_hitl=requires_hitl,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={
                'financial_amount': workflow_data.get('financial_amount', 0),
                'compliance_checks': workflow_data.get('compliance_data', {}),
                'ai_model_type': workflow_data.get('ai_model_type', 'none'),
                'thresholds_exceeded': {
                    'financial': financial_threshold_exceeded,
                    'compliance': compliance_risk > self.thresholds['compliance'],
                    'explainability': explainability_risk > self.thresholds['explainability'],
                    'composite': composite_score > self.thresholds['total']
                }
            }
        )
        
        # Cache the risk score
        self._cache_risk_score(risk_score)
        
        # Queue HITL review if required
        if requires_hitl:
            logger.warning(f"🚨 HITL required for workflow {workflow_id} (score: {composite_score:.3f})")
            self._queue_hitl_review(risk_score)
        else:
            logger.info(f"✅ Workflow {workflow_id} passed risk assessment (score: {composite_score:.3f})")
        
        return risk_score
    
    def _calc_financial_risk(self, workflow_data: Dict[str, Any]) -> float:
        """
        Calculate financial risk based on transaction amounts.
        
        Args:
            workflow_data: Workflow information
            
        Returns:
            Financial risk score (0-1)
        """
        financial_amount = workflow_data.get('financial_amount', 0)
        
        # Normalize to 0-1 scale using sigmoid-like function
        # Risk increases with amount, approaching 1 for very large amounts
        threshold = self.thresholds['financial']
        
        if financial_amount <= 0:
            return 0.0
        
        # Linear scaling up to 2x threshold, then cap at 1.0
        risk = min(financial_amount / (threshold * 2), 1.0)
        
        logger.debug(f"Financial risk: ${financial_amount} -> {risk:.3f}")
        return risk
    
    def _check_compliance(self, workflow_data: Dict[str, Any]) -> float:
        """
        Check compliance requirements and calculate risk.
        
        Args:
            workflow_data: Workflow information
            
        Returns:
            Compliance risk score (0-1, higher is more risky)
        """
        compliance_data = workflow_data.get('compliance_data', {})
        
        if not compliance_data:
            # No compliance data means unknown risk
            return 0.5
        
        # Calculate based on failed checks
        total_checks = len(compliance_data)
        if total_checks == 0:
            return 0.5
        
        failed_checks = sum(1 for v in compliance_data.values() if not v)
        compliance_score = 1.0 - (failed_checks / total_checks)
        
        # Risk is inverse of compliance (1 - score)
        risk = 1.0 - compliance_score
        
        logger.debug(f"Compliance risk: {failed_checks}/{total_checks} failed -> {risk:.3f}")
        return risk
    
    def _assess_explainability(self, workflow_data: Dict[str, Any]) -> float:
        """
        Assess AI model explainability and interpretability.
        
        Args:
            workflow_data: Workflow information
            
        Returns:
            Explainability risk score (0-1, higher is more risky)
        """
        # Check if workflow uses AI
        ai_model_type = workflow_data.get('ai_model_type', 'none')
        
        if ai_model_type == 'none' or not ai_model_type:
            # No AI, no explainability risk
            return 0.0
        
        # Get explainability score if provided
        explainability_score = workflow_data.get('explainability_score')
        
        if explainability_score is not None:
            # Risk is inverse of explainability
            risk = 1.0 - explainability_score
        else:
            # Estimate based on model type
            model_risk_map = {
                'linear': 0.1,
                'tree': 0.2,
                'ensemble': 0.4,
                'neural_network': 0.6,
                'deep_learning': 0.8,
                'llm': 0.7,
                'unknown': 0.5
            }
            risk = model_risk_map.get(ai_model_type.lower(), 0.5)
        
        logger.debug(f"Explainability risk for {ai_model_type}: {risk:.3f}")
        return risk
    
    def _cache_risk_score(self, risk_score: RiskScore) -> None:
        """
        Cache risk score in Redis with expiration.
        
        Args:
            risk_score: RiskScore object to cache
        """
        if self.redis_client is None:
            logger.debug("Redis not available, skipping cache")
            return
        
        try:
            key = f"risk:{risk_score.workflow_id}"
            value = json.dumps(risk_score.to_dict())
            
            # Cache for 24 hours
            expiration = 86400
            
            self.redis_client.setex(key, expiration, value)
            logger.debug(f"Cached risk score for {risk_score.workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache risk score: {e}")
    
    def _queue_hitl_review(self, risk_score: RiskScore) -> None:
        """
        Queue Human-in-the-Loop review using Celery.
        
        Args:
            risk_score: RiskScore object requiring review
        """
        if self.celery_app is None:
            logger.warning("Celery not available, HITL review not queued")
            # Still record in Redis if available
            if self.redis_client:
                try:
                    self.redis_client.set(
                        f"hitl:{risk_score.workflow_id}",
                        "pending_manual_review"
                    )
                except Exception as e:
                    logger.error(f"Failed to record HITL in Redis: {e}")
            return
        
        try:
            # Queue async task for HITL review
            task_data = {
                'workflow_id': risk_score.workflow_id,
                'risk_score': risk_score.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send task to Celery
            # In a real implementation, this would be a defined Celery task
            # For now, we'll just record it in Redis
            if self.redis_client:
                self.redis_client.set(
                    f"hitl:{risk_score.workflow_id}",
                    json.dumps(task_data)
                )
                logger.info(f"✅ Queued HITL review for {risk_score.workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to queue HITL review: {e}")
    
    def get_cached_risk_score(self, workflow_id: str) -> Optional[RiskScore]:
        """
        Retrieve cached risk score from Redis.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            RiskScore object if found, None otherwise
        """
        if self.redis_client is None:
            return None
        
        try:
            key = f"risk:{workflow_id}"
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                return RiskScore(**data)
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached risk score: {e}")
        
        return None
