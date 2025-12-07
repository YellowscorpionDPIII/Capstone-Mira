"""OrchestratorAgent for routing messages between agents."""
from typing import Dict, Any, Optional, List
from mira.core.base_agent import BaseAgent
from mira.core.message_broker import get_broker


class OrchestratorAgent(BaseAgent):
    """
    Agent responsible for orchestrating workflow between other agents.
    
    This agent routes messages to appropriate agents based on message
    type and coordinates multi-agent workflows.
    """
    
    def __init__(self, agent_id: str = "orchestrator_agent", config: Dict[str, Any] = None):
        """Initialize the OrchestratorAgent."""
        super().__init__(agent_id, config)
        self.broker = get_broker()
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.routing_rules = self._initialize_routing_rules()
        self.governance_agent = GovernanceAgent(config=config)
        
    def _initialize_routing_rules(self) -> Dict[str, str]:
        """
        Initialize message routing rules.
        
        Returns:
            Dictionary mapping message types to agent IDs
        """
        return {
            'generate_plan': 'project_plan_agent',
            'update_plan': 'project_plan_agent',
            'assess_risks': 'risk_assessment_agent',
            'update_risk': 'risk_assessment_agent',
            'generate_report': 'status_reporter_agent',
            'schedule_report': 'status_reporter_agent'
        }
        
    def register_agent(self, agent: BaseAgent):
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: Agent to register
        """
        self.agent_registry[agent.agent_id] = agent
        self.logger.info(f"Registered agent: {agent.agent_id}")
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and route a message to the appropriate agent.
        
        Args:
            message: Message to route
            
        Returns:
            Response from the target agent
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            message_type = message['type']
            
            if message_type == 'workflow':
                return self._execute_workflow(message['data'])
            else:
                return self._route_message(message)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return self.create_response('error', None, str(e))
            
    def _route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a message to the appropriate agent.
        
        Args:
            message: Message to route
            
        Returns:
            Response from target agent
        """
        message_type = message['type']
        
        # Determine target agent
        target_agent_id = self.routing_rules.get(message_type)
        
        if not target_agent_id:
            return self.create_response('error', None, f'No routing rule for message type: {message_type}')
            
        target_agent = self.agent_registry.get(target_agent_id)
        
        if not target_agent:
            return self.create_response('error', None, f'Agent not found: {target_agent_id}')
            
        # Route message to target agent
        self.logger.info(f"Routing {message_type} to {target_agent_id}")
        response = target_agent.process(message)
        
        return response
        
    def _execute_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a multi-step workflow.
        
        Args:
            data: Workflow definition
            
        Returns:
            Workflow execution results
        """
        workflow_type = data.get('workflow_type')
        workflow_data = data.get('data', {})
        
        results = {
            'workflow_type': workflow_type,
            'steps': [],
            'governance': {}
        }
        
        if workflow_type == 'project_initialization':
            # Step 1: Generate project plan
            plan_response = self._route_message({
                'type': 'generate_plan',
                'data': workflow_data
            })
            results['steps'].append({
                'step': 'generate_plan',
                'status': plan_response['status'],
                'result': plan_response.get('data')
            })
            
            # Step 2: Assess risks based on plan
            if plan_response['status'] == 'success':
                plan = plan_response['data']
                risk_response = self._route_message({
                    'type': 'assess_risks',
                    'data': plan
                })
                results['steps'].append({
                    'step': 'assess_risks',
                    'status': risk_response['status'],
                    'result': risk_response.get('data')
                })
                
                # Step 3: Perform governance check
                if risk_response['status'] == 'success':
                    risks = risk_response['data']
                    governance_result = self.governance_agent.perform_governance_check(
                        workflow_data, plan, risks
                    )
                    results['governance'] = governance_result
                    results['steps'].append({
                        'step': 'governance_check',
                        'status': 'success',
                        'result': governance_result
                    })
                    
                    # Validate result status based on risk level
                    if governance_result.get('requires_human_review'):
                        results['status'] = 'pending_human_review'
                        results['human_review_reason'] = governance_result.get('review_reason')
                        self.logger.warning(
                            f"Workflow flagged for human review: {governance_result.get('review_reason')}"
                        )
                    else:
                        results['status'] = 'approved'
                
                # Step 4: Generate initial status report
                if risk_response['status'] == 'success':
                    risks = risk_response['data']
                    report_data = {**plan, 'risks': risks.get('risks', [])}
                    report_response = self._route_message({
                        'type': 'generate_report',
                        'data': report_data
                    })
                    results['steps'].append({
                        'step': 'generate_report',
                        'status': report_response['status'],
                        'result': report_response.get('data')
                    })
                    
        self.logger.info(f"Completed workflow: {workflow_type}")
        return results
        
    def add_routing_rule(self, message_type: str, agent_id: str):
        """
        Add a custom routing rule.
        
        Args:
            message_type: Message type to route
            agent_id: Target agent ID
        """
        self.routing_rules[message_type] = agent_id
        self.logger.info(f"Added routing rule: {message_type} -> {agent_id}")


class GovernanceAgent:
    """
    Agent responsible for governance and human-in-the-loop validation.
    
    This agent performs risk assessments based on financial impact, compliance,
    and explainability thresholds to determine if human validation is required.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the GovernanceAgent.
        
        Args:
            config: Optional configuration dictionary with governance thresholds
        """
        self.config = config or {}
        self.thresholds = self._initialize_thresholds()
        
    def _initialize_thresholds(self) -> Dict[str, Any]:
        """
        Initialize governance thresholds from config or defaults.
        
        Returns:
            Dictionary of governance thresholds
        """
        governance_config = self.config.get('governance', {})
        return {
            'financial_impact_threshold': governance_config.get('financial_impact_threshold', 100000),
            'compliance_risk_threshold': governance_config.get('compliance_risk_threshold', 70),
            'explainability_threshold': governance_config.get('explainability_threshold', 0.5),
            'high_risk_score_threshold': governance_config.get('high_risk_score_threshold', 75)
        }
        
    def perform_governance_check(
        self,
        workflow_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        risk_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform governance check on workflow execution.
        
        Args:
            workflow_data: Original workflow data
            plan_data: Generated plan data
            risk_data: Risk assessment data
            
        Returns:
            Governance check results with human review determination
        """
        # Extract relevant data for governance checks
        financial_impact = workflow_data.get('financial_impact', 0)
        compliance_requirements = workflow_data.get('compliance_requirements', [])
        risk_score = risk_data.get('risk_score', 0)
        risks = risk_data.get('risks', [])
        
        # Perform individual checks
        financial_check = self._check_financial_impact(financial_impact)
        compliance_check = self._check_compliance(compliance_requirements, risks)
        explainability_check = self._check_explainability(plan_data, risk_data)
        risk_level_check = self._check_risk_level(risk_score)
        
        # Determine if human validation is required
        requires_review = self._determine_human_validation_required(
            financial_check,
            compliance_check,
            explainability_check,
            risk_level_check
        )
        
        # Build review reasons
        review_reasons = []
        if financial_check['requires_review']:
            review_reasons.append(financial_check['reason'])
        if compliance_check['requires_review']:
            review_reasons.append(compliance_check['reason'])
        if explainability_check['requires_review']:
            review_reasons.append(explainability_check['reason'])
        if risk_level_check['requires_review']:
            review_reasons.append(risk_level_check['reason'])
            
        return {
            'requires_human_review': requires_review,
            'review_reason': '; '.join(review_reasons) if review_reasons else None,
            'financial_check': financial_check,
            'compliance_check': compliance_check,
            'explainability_check': explainability_check,
            'risk_level_check': risk_level_check,
            'thresholds_used': self.thresholds
        }
        
    def _check_financial_impact(self, financial_impact: float) -> Dict[str, Any]:
        """
        Check if financial impact exceeds threshold.
        
        Args:
            financial_impact: Financial impact amount
            
        Returns:
            Check result with requires_review flag
        """
        threshold = self.thresholds['financial_impact_threshold']
        exceeds_threshold = financial_impact > threshold
        
        return {
            'requires_review': exceeds_threshold,
            'financial_impact': financial_impact,
            'threshold': threshold,
            'reason': f'Financial impact (${financial_impact:,.2f}) exceeds threshold (${threshold:,.2f})' 
                     if exceeds_threshold else None
        }
        
    def _check_compliance(
        self,
        compliance_requirements: List[str],
        risks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check compliance requirements and related risks.
        
        Args:
            compliance_requirements: List of compliance requirements
            risks: List of identified risks
            
        Returns:
            Check result with requires_review flag
        """
        # Check if any high-severity compliance-related risks exist
        compliance_risks = [
            r for r in risks 
            if r.get('category') == 'compliance' or 
               any(req.lower() in r.get('description', '').lower() 
                   for req in compliance_requirements)
        ]
        
        high_severity_compliance_risks = [
            r for r in compliance_risks if r.get('severity') == 'high'
        ]
        
        requires_review = len(high_severity_compliance_risks) > 0 or len(compliance_requirements) > 0
        
        reason = None
        if high_severity_compliance_risks:
            reason = f'High-severity compliance risks detected: {len(high_severity_compliance_risks)}'
        elif compliance_requirements:
            reason = f'Compliance requirements present: {", ".join(compliance_requirements[:3])}'
            
        return {
            'requires_review': requires_review,
            'compliance_requirements': compliance_requirements,
            'compliance_risks_count': len(compliance_risks),
            'high_severity_compliance_risks': len(high_severity_compliance_risks),
            'reason': reason
        }
        
    def _check_explainability(
        self,
        plan_data: Dict[str, Any],
        risk_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check explainability of the plan and risk assessment.
        
        Args:
            plan_data: Generated plan data
            risk_data: Risk assessment data
            
        Returns:
            Check result with requires_review flag
        """
        # Calculate explainability score based on documentation completeness
        explainability_score = 0.0
        factors = []
        
        # Check if plan has description
        if plan_data.get('description'):
            explainability_score += 0.2
            factors.append('plan_description')
            
        # Check if plan has milestones
        if plan_data.get('milestones'):
            explainability_score += 0.2
            factors.append('milestones')
            
        # Check if tasks are documented
        if plan_data.get('tasks'):
            explainability_score += 0.2
            factors.append('tasks')
            
        # Check if risks have mitigation strategies
        risks = risk_data.get('risks', [])
        if risks and all(r.get('mitigation') for r in risks):
            explainability_score += 0.2
            factors.append('risk_mitigation')
            
        # Check if risks have descriptions
        if risks and all(r.get('description') for r in risks):
            explainability_score += 0.2
            factors.append('risk_descriptions')
            
        threshold = self.thresholds['explainability_threshold']
        below_threshold = explainability_score < threshold
        
        return {
            'requires_review': below_threshold,
            'explainability_score': round(explainability_score, 2),
            'threshold': threshold,
            'factors_present': factors,
            'reason': f'Explainability score ({explainability_score:.2f}) below threshold ({threshold:.2f})'
                     if below_threshold else None
        }
        
    def _check_risk_level(self, risk_score: float) -> Dict[str, Any]:
        """
        Check if risk level is high.
        
        Args:
            risk_score: Overall risk score
            
        Returns:
            Check result with requires_review flag
        """
        threshold = self.thresholds['high_risk_score_threshold']
        is_high_risk = risk_score >= threshold
        
        return {
            'requires_review': is_high_risk,
            'risk_score': risk_score,
            'threshold': threshold,
            'risk_level': 'high' if is_high_risk else 'medium' if risk_score >= 50 else 'low',
            'reason': f'Risk score ({risk_score:.2f}) exceeds high-risk threshold ({threshold:.2f})'
                     if is_high_risk else None
        }
        
    def _determine_human_validation_required(
        self,
        financial_check: Dict[str, Any],
        compliance_check: Dict[str, Any],
        explainability_check: Dict[str, Any],
        risk_level_check: Dict[str, Any]
    ) -> bool:
        """
        Determine if human validation is required based on all checks.
        
        Args:
            financial_check: Financial impact check result
            compliance_check: Compliance check result
            explainability_check: Explainability check result
            risk_level_check: Risk level check result
            
        Returns:
            True if human validation is required, False otherwise
        """
        return (
            financial_check['requires_review'] or
            compliance_check['requires_review'] or
            explainability_check['requires_review'] or
            risk_level_check['requires_review']
        )
