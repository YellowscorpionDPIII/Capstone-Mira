"""RoadmappingAgent for generating AI roadmaps and tracking KPIs."""
from typing import Dict, List, Any
from mira.core.base_agent import BaseAgent
from mira.integrations.airtable_integration import AirtableIntegration


class RoadmappingAgent(BaseAgent):
    """
    Agent responsible for generating AI roadmaps and tracking KPI progress.
    
    This agent creates prioritized AI roadmaps aligned to business objectives,
    calculates EBIT projections, and tracks initiative KPIs using Airtable data.
    """
    
    def __init__(self, agent_id: str = "roadmapping_agent", config: Dict[str, Any] = None):
        """Initialize the RoadmappingAgent."""
        super().__init__(agent_id, config)
        self.objectives = ["efficiency", "growth", "innovation"]
        self.kpi_weights = {"ebit_impact": 0.4, "revenue": 0.3, "cost_save": 0.3}
        self.airtable = AirtableIntegration(config)
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a roadmapping request.
        
        Args:
            message: Message containing roadmap or KPI tracking request
            
        Returns:
            Generated roadmap or KPI progress data
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            data = message['data']
            message_type = message['type']
            
            if message_type == 'generate_roadmap':
                roadmap = self._generate_roadmap(data)
                return self.create_response('success', roadmap)
            elif message_type == 'track_kpi_progress':
                kpi_progress = self._track_kpi_progress(data)
                return self.create_response('success', kpi_progress)
            else:
                return self.create_response('error', None, f'Unknown message type: {message_type}')
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return self.create_response('error', None, str(e))

    def _generate_roadmap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate prioritized AI roadmap aligned to business objectives.
        
        Args:
            data: Dictionary containing business_objectives list
            
        Returns:
            Roadmap with initiatives, EBIT projection, and timeline
        """
        business_objectives = data.get('business_objectives', [])
        
        roadmap = {
            "initiatives": [],
            "ebit_projection": 0.0,
            "timeline": {}
        }
        
        for objective in business_objectives:
            initiatives = self._prioritize_initiatives(objective)
            roadmap["initiatives"].extend(initiatives)
            
        roadmap["ebit_projection"] = self._calculate_ebit_impact(roadmap["initiatives"])
        roadmap["generated_by"] = self.agent_id
        
        self.logger.info(f"Generated roadmap with {len(roadmap['initiatives'])} initiatives")
        return roadmap
    
    def _prioritize_initiatives(self, objective: str) -> List[Dict[str, Any]]:
        """
        Prioritize initiatives based on objective.
        
        Args:
            objective: Business objective to align initiatives with
            
        Returns:
            List of prioritized initiatives
        """
        # Generate sample initiatives based on objective
        # In production, this would integrate with more sophisticated prioritization
        initiatives = []
        
        if objective.lower() in ["efficiency", "cost reduction"]:
            initiatives.append({
                "name": f"Automate {objective} processes",
                "objective": objective,
                "ebit_impact": 0.25,
                "revenue": 0.1,
                "cost_save": 0.35,
                "scale_factor": 1.2,
                "priority": "high",
                "timeline_weeks": 12
            })
        elif objective.lower() in ["growth", "revenue"]:
            initiatives.append({
                "name": f"AI-driven {objective} optimization",
                "objective": objective,
                "ebit_impact": 0.30,
                "revenue": 0.40,
                "cost_save": 0.15,
                "scale_factor": 1.5,
                "priority": "high",
                "timeline_weeks": 16
            })
        elif objective.lower() in ["innovation", "transformation"]:
            initiatives.append({
                "name": f"Innovative {objective} solutions",
                "objective": objective,
                "ebit_impact": 0.20,
                "revenue": 0.25,
                "cost_save": 0.20,
                "scale_factor": 1.0,
                "priority": "medium",
                "timeline_weeks": 20
            })
        else:
            # Generic initiative for other objectives
            initiatives.append({
                "name": f"AI initiative for {objective}",
                "objective": objective,
                "ebit_impact": 0.15,
                "revenue": 0.20,
                "cost_save": 0.25,
                "scale_factor": 1.0,
                "priority": "medium",
                "timeline_weeks": 14
            })
            
        return initiatives

    def _calculate_ebit_impact(self, initiatives: List[Dict]) -> float:
        """
        Calculate projected EBIT impact from initiatives.
        
        Args:
            initiatives: List of initiative dictionaries with KPI values
            
        Returns:
            Total projected EBIT impact as a float
        """
        total_ebit = 0.0
        for init in initiatives:
            score = sum(self.kpi_weights[k] * init.get(k, 0) for k in self.kpi_weights)
            total_ebit += score * init.get("scale_factor", 1.0)
        return round(total_ebit, 2)

    def _track_kpi_progress(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track EBIT attribution and KPIs for an initiative.
        
        Args:
            data: Dictionary containing initiative_id
            
        Returns:
            Dictionary with EBIT attribution, revenue impact, and cost savings
        """
        initiative_id = data.get('initiative_id', '')
        
        # Get KPI data from Airtable
        airtable_data = self._get_kpis_from_airtable(initiative_id)
        
        kpi_progress = {
            "initiative_id": initiative_id,
            "ebit_attribution": airtable_data.get("ebit_pct", 0.0),
            "revenue_impact": airtable_data.get("revenue_change", 0.0),
            "cost_savings": airtable_data.get("cost_reduction", 0.0),
            "tracked_by": self.agent_id
        }
        
        self.logger.info(f"Tracked KPI progress for initiative: {initiative_id}")
        return kpi_progress
    
    def _get_kpis_from_airtable(self, initiative_id: str) -> Dict[str, Any]:
        """
        Retrieve KPI data from Airtable for a given initiative.
        
        Args:
            initiative_id: Unique identifier for the initiative
            
        Returns:
            Dictionary containing KPI values from Airtable
        """
        # Connect to Airtable if not already connected
        if not self.airtable.connected:
            self.airtable.connect()
        
        # In production, this would query Airtable API for specific initiative
        # For now, return simulated data
        return {
            "ebit_pct": 0.18,
            "revenue_change": 0.22,
            "cost_reduction": 0.15,
            "last_updated": "2025-12-07"
        }
