"""GovernanceAgent for risk assessment and human-in-the-loop validation."""
from typing import Dict, Any, Optional
from mira.core.base_agent import BaseAgent


class GovernanceAgent(BaseAgent):
    """
    Agent responsible for governance, risk assessment, and determining
    when human-in-the-loop validation is required.
    
    This agent evaluates workflow decisions based on:
    - Financial impact thresholds
    - Compliance requirements
    - Explainability scores
    """
    
    def __init__(self, agent_id: str = "governance_agent", config: Dict[str, Any] = None):
        """
        Initialize the GovernanceAgent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Optional configuration dictionary with thresholds
        """
        super().__init__(agent_id, config)
        
        # Default thresholds (can be overridden via config)
        self.financial_threshold = self.config.get('financial_threshold', 10000)
        self.compliance_threshold = self.config.get('compliance_threshold', 'medium')
        self.explainability_threshold = self.config.get('explainability_threshold', 0.7)
        
        # Map compliance levels to numeric values for comparison
        self.compliance_levels = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process governance-related messages.
        
        Args:
            message: Message containing governance request
            
        Returns:
            Response with governance assessment
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            message_type = message['type']
            data = message['data']
            
            if message_type == 'assess_governance':
                return self._assess_governance(data)
            elif message_type == 'check_human_validation':
                return self._check_human_validation(data)
            else:
                return self.create_response('error', None, f'Unknown message type: {message_type}')
                
        except Exception as e:
            self.logger.error(f"Error processing governance message: {e}")
            return self.create_response('error', None, str(e))
            
    def _assess_governance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess governance requirements for a workflow or decision.
        
        Args:
            data: Workflow data to assess
            
        Returns:
            Governance assessment with risk level and validation requirements
        """
        assessment = {
            'financial_impact': data.get('financial_impact', 0),
            'compliance_level': data.get('compliance_level', 'low'),
            'explainability_score': data.get('explainability_score', 1.0),
            'risk_level': 'low',
            'requires_human_validation': False,
            'reasons': []
        }
        
        # Check financial impact
        if assessment['financial_impact'] > self.financial_threshold:
            assessment['risk_level'] = 'high'
            assessment['requires_human_validation'] = True
            assessment['reasons'].append(
                f"Financial impact ${assessment['financial_impact']} exceeds threshold ${self.financial_threshold}"
            )
            
        # Check compliance requirements
        compliance_value = self.compliance_levels.get(assessment['compliance_level'], 0)
        threshold_value = self.compliance_levels.get(self.compliance_threshold, 2)
        
        if compliance_value >= threshold_value:
            if assessment['risk_level'] != 'high':
                assessment['risk_level'] = 'medium'
            if compliance_value >= self.compliance_levels.get('high', 3):
                assessment['requires_human_validation'] = True
            assessment['reasons'].append(
                f"Compliance level '{assessment['compliance_level']}' requires review"
            )
            
        # Check explainability score (lower score = less explainable = higher risk)
        if assessment['explainability_score'] < self.explainability_threshold:
            if assessment['risk_level'] == 'low':
                assessment['risk_level'] = 'medium'
            assessment['requires_human_validation'] = True
            assessment['reasons'].append(
                f"Explainability score {assessment['explainability_score']:.2f} below threshold {self.explainability_threshold}"
            )
            
        self.logger.info(
            f"Governance assessment: risk_level={assessment['risk_level']}, "
            f"requires_human_validation={assessment['requires_human_validation']}"
        )
        
        return self.create_response('success', assessment)
        
    def _check_human_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if human validation is required for the given data.
        
        Args:
            data: Data to check
            
        Returns:
            Response indicating if human validation is required
        """
        # Perform assessment
        assessment_response = self._assess_governance(data)
        
        if assessment_response['status'] == 'success':
            assessment = assessment_response['data']
            result = {
                'requires_validation': assessment['requires_human_validation'],
                'risk_level': assessment['risk_level'],
                'reasons': assessment['reasons']
            }
            return self.create_response('success', result)
        else:
            return assessment_response
            
    def update_thresholds(self, thresholds: Dict[str, Any]):
        """
        Update governance thresholds.
        
        Args:
            thresholds: Dictionary with new threshold values
        """
        if 'financial_threshold' in thresholds:
            self.financial_threshold = thresholds['financial_threshold']
            self.logger.info(f"Updated financial_threshold to {self.financial_threshold}")
            
        if 'compliance_threshold' in thresholds:
            self.compliance_threshold = thresholds['compliance_threshold']
            self.logger.info(f"Updated compliance_threshold to {self.compliance_threshold}")
            
        if 'explainability_threshold' in thresholds:
            self.explainability_threshold = thresholds['explainability_threshold']
            self.logger.info(f"Updated explainability_threshold to {self.explainability_threshold}")
