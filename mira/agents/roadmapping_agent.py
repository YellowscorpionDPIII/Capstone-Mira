# mira/agents/roadmapping_agent.py
from typing import Dict, List, Any
from mira.agents.base_agent import BaseAgent
from mira.integrations.airtable import AirtableConnector

class RoadmappingAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="roadmapping")
        self.objectives = ["efficiency", "growth", "innovation"]
        self.kpi_weights = {"ebit_impact": 0.4, "revenue": 0.3, "cost_save": 0.3}

    async def generate_roadmap(self, business_objectives: List[str]) -> Dict[str, Any]:
        """Generate prioritized AI roadmap aligned to objectives"""
        roadmap = {
            "initiatives": [],
            "ebit_projection": 0.0,
            "timeline": {}
        }
        
        for objective in business_objectives:
            initiatives = await self._prioritize_initiatives(objective)
            roadmap["initiatives"].extend(initiatives)
            
        roadmap["ebit_projection"] = self._calculate_ebit_impact(roadmap["initiatives"])
        return roadmap

    def _calculate_ebit_impact(self, initiatives: List[Dict]) -> float:
        """Calculate projected EBIT impact"""
        total_ebit = 0.0
        for init in initiatives:
            score = sum(self.kpi_weights[k] * init.get(k, 0) for k in self.kpi_weights)
            total_ebit += score * init.get("scale_factor", 1.0)
        return total_ebit

    async def track_kpi_progress(self, initiative_id: str) -> Dict[str, float]:
        """Track EBIT attribution and KPIs"""
        airtable_data = await AirtableConnector.get_kpis(initiative_id)
        return {
            "ebit_attribution": airtable_data.get("ebit_pct", 0.0),
            "revenue_impact": airtable_data.get("revenue_change", 0.0),
            "cost_savings": airtable_data.get("cost_reduction", 0.0)
        }
