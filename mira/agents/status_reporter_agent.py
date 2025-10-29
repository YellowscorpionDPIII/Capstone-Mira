"""StatusReporterAgent for generating weekly status reports."""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from mira.core.base_agent import BaseAgent


class StatusReporterAgent(BaseAgent):
    """
    Agent responsible for generating weekly status reports.
    
    This agent aggregates project data and creates formatted status
    reports for stakeholders.
    """
    
    def __init__(self, agent_id: str = "status_reporter_agent", config: Dict[str, Any] = None):
        """Initialize the StatusReporterAgent."""
        super().__init__(agent_id, config)
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a status report request.
        
        Args:
            message: Message containing project data
            
        Returns:
            Generated status report
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            data = message['data']
            message_type = message['type']
            
            if message_type == 'generate_report':
                report = self._generate_report(data)
                return self.create_response('success', report)
            elif message_type == 'schedule_report':
                schedule = self._schedule_report(data)
                return self.create_response('success', schedule)
            else:
                return self.create_response('error', None, f'Unknown message type: {message_type}')
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return self.create_response('error', None, str(e))
            
    def _generate_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a weekly status report.
        
        Args:
            data: Project data including tasks, milestones, risks
            
        Returns:
            Formatted status report
        """
        project_name = data.get('name', 'Unknown Project')
        tasks = data.get('tasks', [])
        milestones = data.get('milestones', [])
        risks = data.get('risks', [])
        week_number = data.get('week_number', 1)
        
        # Calculate task statistics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get('status') == 'completed'])
        in_progress_tasks = len([t for t in tasks if t.get('status') == 'in_progress'])
        not_started_tasks = len([t for t in tasks if t.get('status') == 'not_started'])
        
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Identify upcoming milestones
        upcoming_milestones = [
            m for m in milestones 
            if m.get('week', 0) >= week_number and m.get('week', 0) <= week_number + 2
        ]
        
        # Identify high-priority risks
        high_risks = [r for r in risks if r.get('severity') == 'high']
        
        # Generate accomplishments
        accomplishments = [
            f"Completed {completed_tasks} tasks this week"
        ]
        if completed_tasks > 0:
            completed_task_names = [t.get('name', 'Unknown') for t in tasks if t.get('status') == 'completed'][:3]
            accomplishments.extend(completed_task_names)
            
        # Generate next week's plan
        next_week_plan = [
            f"Continue work on {in_progress_tasks} in-progress tasks"
        ]
        if not_started_tasks > 0:
            next_week_plan.append(f"Start {min(not_started_tasks, 5)} new tasks")
            
        # Generate report
        report = {
            'project_name': project_name,
            'report_date': datetime.utcnow().isoformat(),
            'week_number': week_number,
            'summary': {
                'completion_percentage': round(completion_percentage, 2),
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'not_started_tasks': not_started_tasks
            },
            'accomplishments': accomplishments,
            'upcoming_milestones': [
                {'name': m.get('name'), 'week': m.get('week')} 
                for m in upcoming_milestones
            ],
            'risks_and_blockers': [
                {'id': r.get('id'), 'description': r.get('description'), 'severity': r.get('severity')} 
                for r in high_risks
            ],
            'next_week_plan': next_week_plan,
            'generated_by': self.agent_id
        }
        
        self.logger.info(f"Generated status report for {project_name} - Week {week_number}")
        return report
        
    def _schedule_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule recurring status reports.
        
        Args:
            data: Scheduling parameters
            
        Returns:
            Schedule configuration
        """
        frequency = data.get('frequency', 'weekly')
        recipients = data.get('recipients', [])
        day_of_week = data.get('day_of_week', 'Friday')
        
        schedule = {
            'frequency': frequency,
            'recipients': recipients,
            'day_of_week': day_of_week,
            'next_run': self._calculate_next_run(day_of_week),
            'created_by': self.agent_id
        }
        
        self.logger.info(f"Scheduled {frequency} reports for {len(recipients)} recipients")
        return schedule
        
    def _calculate_next_run(self, day_of_week: str) -> str:
        """
        Calculate the next report run date.
        
        Args:
            day_of_week: Target day of week
            
        Returns:
            ISO formatted date string
        """
        days = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 
            'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        
        today = datetime.utcnow()
        target_day = days.get(day_of_week, 4)  # Default to Friday
        days_ahead = (target_day - today.weekday()) % 7
        
        if days_ahead == 0:
            days_ahead = 7
            
        next_run = today + timedelta(days=days_ahead)
        return next_run.isoformat()
