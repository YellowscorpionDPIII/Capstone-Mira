"""ProjectPlanAgent for generating project plans."""
from typing import Dict, Any
from mira.core.base_agent import BaseAgent


class ProjectPlanAgent(BaseAgent):
    """
    Agent responsible for generating project plans.
    
    This agent analyzes project requirements and creates structured
    project plans including milestones, tasks, and timelines.
    """
    
    def __init__(self, agent_id: str = "project_plan_agent", config: Dict[str, Any] = None):
        """Initialize the ProjectPlanAgent."""
        super().__init__(agent_id, config)
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a project planning request.
        
        Args:
            message: Message containing project requirements
            
        Returns:
            Project plan with milestones and tasks
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            data = message['data']
            message_type = message['type']
            
            if message_type == 'generate_plan':
                plan = self._generate_plan(data)
                return self.create_response('success', plan)
            elif message_type == 'update_plan':
                plan = self._update_plan(data)
                return self.create_response('success', plan)
            else:
                return self.create_response('error', None, f'Unknown message type: {message_type}')
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return self.create_response('error', None, str(e))
            
    def _generate_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a project plan from requirements.
        
        Args:
            data: Project requirements including name, description, goals
            
        Returns:
            Generated project plan
        """
        project_name = data.get('name', 'Unnamed Project')
        description = data.get('description', '')
        goals = data.get('goals', [])
        duration_weeks = data.get('duration_weeks', 12)
        
        # Generate milestones based on goals
        milestones = []
        for i, goal in enumerate(goals, 1):
            milestone = {
                'id': f'M{i}',
                'name': goal,
                'week': (i * duration_weeks) // len(goals) if goals else 1,
                'deliverables': [f'Deliverable for {goal}'],
                'status': 'not_started'
            }
            milestones.append(milestone)
            
        # Generate tasks
        tasks = []
        for milestone in milestones:
            for j in range(3):  # 3 tasks per milestone
                task = {
                    'id': f'{milestone["id"]}-T{j+1}',
                    'milestone_id': milestone['id'],
                    'name': f'Task {j+1} for {milestone["name"]}',
                    'status': 'not_started',
                    'priority': 'medium',
                    'estimated_hours': 8
                }
                tasks.append(task)
                
        plan = {
            'name': project_name,
            'description': description,
            'duration_weeks': duration_weeks,
            'milestones': milestones,
            'tasks': tasks,
            'created_by': self.agent_id
        }
        
        self.logger.info(f"Generated plan for project: {project_name}")
        return plan
        
    def _update_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing project plan.
        
        Args:
            data: Plan updates
            
        Returns:
            Updated plan
        """
        plan = data.get('plan', {})
        updates = data.get('updates', {})
        
        # Apply updates
        plan.update(updates)
        
        self.logger.info(f"Updated plan: {plan.get('name', 'Unknown')}")
        return plan
