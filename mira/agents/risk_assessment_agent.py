"""RiskAssessmentAgent for analyzing project risks."""
from typing import Dict, Any, List
from mira.core.base_agent import BaseAgent


class RiskAssessmentAgent(BaseAgent):
    """
    Agent responsible for identifying and assessing project risks.
    
    This agent analyzes project data to identify potential risks,
    assigns severity levels, and suggests mitigation strategies.
    """
    
    def __init__(self, agent_id: str = "risk_assessment_agent", config: Dict[str, Any] = None):
        """Initialize the RiskAssessmentAgent."""
        super().__init__(agent_id, config)
        self.risk_database = self._initialize_risk_database()
        
    def _initialize_risk_database(self) -> List[Dict[str, Any]]:
        """
        Initialize a database of common risk patterns.
        
        Returns:
            List of risk patterns
        """
        return [
            {
                'category': 'schedule',
                'pattern': 'tight_deadline',
                'keywords': ['urgent', 'asap', 'short timeline'],
                'severity': 'high',
                'mitigation': 'Add buffer time, reduce scope, or increase resources'
            },
            {
                'category': 'technical',
                'pattern': 'new_technology',
                'keywords': ['new', 'unfamiliar', 'learning'],
                'severity': 'medium',
                'mitigation': 'Allocate time for training and proof-of-concept'
            },
            {
                'category': 'resource',
                'pattern': 'limited_resources',
                'keywords': ['limited', 'insufficient', 'lack of'],
                'severity': 'high',
                'mitigation': 'Secure additional resources or adjust project scope'
            },
            {
                'category': 'dependency',
                'pattern': 'external_dependency',
                'keywords': ['depends on', 'waiting for', 'third party'],
                'severity': 'medium',
                'mitigation': 'Establish clear SLAs and backup plans'
            }
        ]
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a risk assessment request.
        
        Args:
            message: Message containing project data
            
        Returns:
            Risk assessment results
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            data = message['data']
            message_type = message['type']
            
            if message_type == 'assess_risks':
                assessment = self._assess_risks(data)
                return self.create_response('success', assessment)
            elif message_type == 'update_risk':
                updated_risk = self._update_risk(data)
                return self.create_response('success', updated_risk)
            else:
                return self.create_response('error', None, f'Unknown message type: {message_type}')
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return self.create_response('error', None, str(e))
            
    def _assess_risks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform risk assessment on project data.
        
        Args:
            data: Project information
            
        Returns:
            Risk assessment report
        """
        project_name = data.get('name', 'Unknown Project')
        description = data.get('description', '').lower()
        tasks = data.get('tasks', [])
        duration = data.get('duration_weeks', 0)
        
        identified_risks = []
        
        # Analyze description for risk keywords
        for risk_pattern in self.risk_database:
            for keyword in risk_pattern['keywords']:
                if keyword in description:
                    risk = {
                        'id': f'R{len(identified_risks) + 1}',
                        'category': risk_pattern['category'],
                        'pattern': risk_pattern['pattern'],
                        'severity': risk_pattern['severity'],
                        'description': f'Potential {risk_pattern["category"]} risk detected',
                        'mitigation': risk_pattern['mitigation'],
                        'status': 'identified'
                    }
                    identified_risks.append(risk)
                    break
                    
        # Check for schedule risks based on task count and duration
        if len(tasks) > 0 and duration > 0:
            tasks_per_week = len(tasks) / duration
            if tasks_per_week > 5:
                risk = {
                    'id': f'R{len(identified_risks) + 1}',
                    'category': 'schedule',
                    'pattern': 'high_task_density',
                    'severity': 'high',
                    'description': f'High task density: {tasks_per_week:.1f} tasks per week',
                    'mitigation': 'Consider extending timeline or adding resources',
                    'status': 'identified'
                }
                identified_risks.append(risk)
                
        # Calculate overall risk score
        severity_scores = {'low': 1, 'medium': 2, 'high': 3}
        total_score = sum(severity_scores.get(r['severity'], 0) for r in identified_risks)
        max_score = len(identified_risks) * 3
        risk_score = (total_score / max_score * 100) if max_score > 0 else 0
        
        assessment = {
            'project_name': project_name,
            'risk_score': round(risk_score, 2),
            'total_risks': len(identified_risks),
            'risks': identified_risks,
            'assessed_by': self.agent_id
        }
        
        self.logger.info(f"Assessed risks for project: {project_name} (Score: {risk_score})")
        return assessment
        
    def _update_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a risk's status or mitigation plan.
        
        Args:
            data: Risk update information
            
        Returns:
            Updated risk
        """
        risk = data.get('risk', {})
        updates = data.get('updates', {})
        
        risk.update(updates)
        
        self.logger.info(f"Updated risk: {risk.get('id', 'Unknown')}")
        return risk
