"""
Scenario modeling for Importobot demo cases.

This module provides modeling for different business scenarios,
industry types, and test case contexts.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict

# Import from local demo_config module
import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from .demo_config import BusinessMetrics, EnterpriseScenario

# Imports are now at the top of the file


class TimelineScenarioData(TypedDict):
    """Type definition for timeline scenario data."""

    scenario: EnterpriseScenario
    timeline: str
    pressure_multiplier: float
    description: str
    metrics: dict[str, Any]


class ScaleScenarioData(TypedDict):
    """Type definition for scale scenario data."""

    name: str
    test_cases: int
    team_size: int
    characteristics: str


class RiskData(TypedDict):
    """Type definition for risk data."""

    probability: float
    impact_multiplier: float
    description: str


class IndustryVertical(Enum):
    """Industry verticals with different testing characteristics."""

    FINANCIAL_SERVICES = "financial_services"
    HEALTHCARE = "healthcare"
    ECOMMERCE = "ecommerce"
    TELECOMMUNICATIONS = "telecommunications"
    MANUFACTURING = "manufacturing"
    GOVERNMENT = "government"
    GAMING = "gaming"
    SAAS = "saas"


class ProjectComplexity(Enum):
    """Project complexity levels affecting conversion time and cost."""

    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


@dataclass
class IndustryCharacteristics:
    """Characteristics specific to an industry vertical."""

    compliance_overhead: float = 1.0  # Multiplier for compliance requirements
    test_complexity_factor: float = 1.0  # Base test complexity
    documentation_requirements: float = 1.0  # Documentation overhead
    integration_complexity: float = 1.0  # System integration complexity
    risk_tolerance: float = 0.5  # Risk tolerance (0-1, lower = less tolerant)


class ScenarioModeler:
    """Advanced scenario modeling for business case analysis."""

    def __init__(self) -> None:
        """Initialize the scenario modeler with industry characteristics."""
        self.industry_characteristics = {
            IndustryVertical.FINANCIAL_SERVICES: IndustryCharacteristics(
                compliance_overhead=1.8,
                test_complexity_factor=1.5,
                documentation_requirements=2.0,
                integration_complexity=1.7,
                risk_tolerance=0.2,
            ),
            IndustryVertical.HEALTHCARE: IndustryCharacteristics(
                compliance_overhead=2.0,
                test_complexity_factor=1.4,
                documentation_requirements=2.2,
                integration_complexity=1.6,
                risk_tolerance=0.1,
            ),
            IndustryVertical.ECOMMERCE: IndustryCharacteristics(
                compliance_overhead=1.2,
                test_complexity_factor=1.1,
                documentation_requirements=1.0,
                integration_complexity=1.3,
                risk_tolerance=0.7,
            ),
            IndustryVertical.TELECOMMUNICATIONS: IndustryCharacteristics(
                compliance_overhead=1.4,
                test_complexity_factor=1.6,
                documentation_requirements=1.5,
                integration_complexity=1.8,
                risk_tolerance=0.4,
            ),
            IndustryVertical.MANUFACTURING: IndustryCharacteristics(
                compliance_overhead=1.3,
                test_complexity_factor=1.2,
                documentation_requirements=1.4,
                integration_complexity=1.5,
                risk_tolerance=0.5,
            ),
            IndustryVertical.GOVERNMENT: IndustryCharacteristics(
                compliance_overhead=2.5,
                test_complexity_factor=1.3,
                documentation_requirements=3.0,
                integration_complexity=1.4,
                risk_tolerance=0.1,
            ),
            IndustryVertical.GAMING: IndustryCharacteristics(
                compliance_overhead=1.0,
                test_complexity_factor=1.2,
                documentation_requirements=0.8,
                integration_complexity=1.1,
                risk_tolerance=0.8,
            ),
            IndustryVertical.SAAS: IndustryCharacteristics(
                compliance_overhead=1.1,
                test_complexity_factor=1.0,
                documentation_requirements=1.1,
                integration_complexity=1.2,
                risk_tolerance=0.6,
            ),
        }

        self.complexity_multipliers = {
            ProjectComplexity.SIMPLE: 0.7,
            ProjectComplexity.STANDARD: 1.0,
            ProjectComplexity.COMPLEX: 1.5,
            ProjectComplexity.ENTERPRISE: 2.2,
        }

    def create_industry_scenario(
        self,
        industry: IndustryVertical,
        name: str,
        test_cases: int,
        team_size: int,
        *,
        complexity: ProjectComplexity = ProjectComplexity.STANDARD,
    ) -> EnterpriseScenario:
        """Create a scenario tailored for a specific industry."""
        characteristics = self.industry_characteristics[industry]
        complexity_multiplier = self.complexity_multipliers[complexity]

        # Calculate combined complexity factor
        total_complexity = (
            characteristics.test_complexity_factor
            * characteristics.compliance_overhead
            * complexity_multiplier
        )

        # Create scenario with industry-specific adjustments
        scenario = EnterpriseScenario(
            name=f"{name} ({industry.value.replace('_', ' ').title()})",
            test_cases=test_cases,
            team_size=team_size,
            complexity_factor=total_complexity,
        )

        return scenario

    def model_timeline_scenarios(
        self, base_scenario: EnterpriseScenario, base_metrics: BusinessMetrics
    ) -> list[dict[str, Any]]:
        """Model different timeline scenarios (normal, accelerated, rush)."""
        scenarios = []

        # Normal timeline
        normal_scenario = EnterpriseScenario(
            name=f"{base_scenario.name} - Normal Timeline",
            test_cases=base_scenario.test_cases,
            team_size=base_scenario.team_size,
            complexity_factor=base_scenario.complexity_factor,
        )
        scenarios.append(
            {
                "scenario": normal_scenario,
                "timeline": "normal",
                "pressure_multiplier": 1.0,
                "description": "Standard project timeline with normal resources",
            }
        )

        # Accelerated timeline (50% more team members)
        accelerated_scenario = EnterpriseScenario(
            name=f"{base_scenario.name} - Accelerated",
            test_cases=base_scenario.test_cases,
            team_size=int(base_scenario.team_size * 1.5),
            complexity_factor=base_scenario.complexity_factor
            * 1.1,  # Coordination overhead
        )
        scenarios.append(
            {
                "scenario": accelerated_scenario,
                "timeline": "accelerated",
                "pressure_multiplier": 1.2,
                "description": "Accelerated timeline with increased team size",
            }
        )

        # Rush timeline (double team, high pressure)
        rush_scenario = EnterpriseScenario(
            name=f"{base_scenario.name} - Rush",
            test_cases=base_scenario.test_cases,
            team_size=base_scenario.team_size * 2,
            complexity_factor=base_scenario.complexity_factor
            * 1.3,  # High coordination overhead
            urgency_multiplier=1.5,  # Stress factor
        )
        scenarios.append(
            {
                "scenario": rush_scenario,
                "timeline": "rush",
                "pressure_multiplier": 2.0,
                "description": "Rush project with tight deadline and high pressure",
            }
        )

        # Calculate metrics for each scenario
        for scenario_data in scenarios:
            scenario: EnterpriseScenario = scenario_data["scenario"]  # type: ignore
            metrics = scenario.calculate_metrics(base_metrics)

            # Add timeline-specific adjustments
            pressure = float(scenario_data["pressure_multiplier"])  # type: ignore
            metrics["stress_factor"] = pressure
            metrics["coordination_overhead"] = (
                float(scenario.team_size - base_scenario.team_size)
            ) * 0.1
            metrics["risk_multiplier"] = pressure * 0.5  # Higher pressure = higher risk

            scenario_data["metrics"] = metrics

        return scenarios

    def model_scale_scenarios(
        self, base_metrics: BusinessMetrics
    ) -> list[dict[str, Any]]:
        """Model scenarios at different scales (startup to enterprise)."""
        scale_scenarios: list[ScaleScenarioData] = [
            {
                "name": "Startup",
                "test_cases": 50,
                "team_size": 1,
                "characteristics": "Small team, simple processes, high agility",
            },
            {
                "name": "Small Business",
                "test_cases": 200,
                "team_size": 3,
                "characteristics": "Growing team, establishing processes",
            },
            {
                "name": "Mid-Market",
                "test_cases": 800,
                "team_size": 8,
                "characteristics": "Established processes, quality focus",
            },
            {
                "name": "Enterprise",
                "test_cases": 2500,
                "team_size": 20,
                "characteristics": "Complex processes, compliance requirements",
            },
            {
                "name": "Global Enterprise",
                "test_cases": 8000,
                "team_size": 50,
                "characteristics": "Multi-region, high complexity, strict governance",
            },
        ]

        scenarios = []
        for scale_data in scale_scenarios:
            scenario = EnterpriseScenario(
                name=str(scale_data["name"]),
                test_cases=int(scale_data["test_cases"]),
                team_size=int(scale_data["team_size"]),
                complexity_factor=1.0 + (int(scale_data["test_cases"]) / 10000),
            )

            metrics = scenario.calculate_metrics(base_metrics)
            scenarios.append(
                {
                    "scenario": scenario,
                    "metrics": metrics,
                    "characteristics": scale_data["characteristics"],
                }
            )

        return scenarios

    def model_risk_scenarios(
        self, base_scenario: EnterpriseScenario, base_metrics: BusinessMetrics
    ) -> dict[str, dict[str, Any]]:
        """Model risk scenarios for manual vs automated approaches."""
        # Manual approach risks
        manual_risks: dict[str, RiskData] = {
            "human_error": {
                "probability": 0.25,  # 25% chance per project
                "impact_multiplier": 1.5,  # 50% cost increase
                "description": "Human errors requiring rework",
            },
            "timeline_overrun": {
                "probability": 0.60,  # 60% chance
                "impact_multiplier": 1.3,  # 30% time increase
                "description": "Project timeline overruns",
            },
            "quality_issues": {
                "probability": 0.40,  # 40% chance
                "impact_multiplier": 1.2,  # 20% additional QA cost
                "description": "Quality issues requiring fixes",
            },
            "staff_turnover": {
                "probability": 0.20,  # 20% chance
                "impact_multiplier": 2.0,  # 100% cost for knowledge transfer
                "description": "Key staff leaving during project",
            },
        }

        # Automated approach risks
        automated_risks: dict[str, RiskData] = {
            "tool_learning_curve": {
                "probability": 0.80,  # 80% chance (expected)
                "impact_multiplier": 1.05,  # 5% initial overhead
                "description": "Initial learning curve for automation tool",
            },
            "edge_case_handling": {
                "probability": 0.15,  # 15% chance
                "impact_multiplier": 1.1,  # 10% additional manual work
                "description": "Handling complex edge cases manually",
            },
            "tool_limitation": {
                "probability": 0.05,  # 5% chance
                "impact_multiplier": 1.15,  # 15% workaround cost
                "description": "Tool limitations requiring workarounds",
            },
        }

        base_manual_metrics = base_scenario.calculate_metrics(base_metrics)

        # Calculate risk-adjusted metrics
        manual_expected_cost = base_manual_metrics["manual_cost_usd"]
        auto_expected_cost = base_manual_metrics["importobot_cost_usd"]

        # Apply risk probabilities and impacts
        for _risk_name, risk_data in manual_risks.items():
            risk_dict = dict(risk_data)
            expected_impact = float(risk_dict["probability"]) * (  # type: ignore
                float(risk_dict["impact_multiplier"]) - 1  # type: ignore[arg-type]
            )
            manual_expected_cost *= 1 + expected_impact

        for _risk_name, risk_data in automated_risks.items():
            risk_dict = dict(risk_data)
            expected_impact = float(risk_dict["probability"]) * (  # type: ignore
                float(risk_dict["impact_multiplier"]) - 1  # type: ignore[arg-type]
            )
            auto_expected_cost *= 1 + expected_impact

        return {
            "manual_risks": manual_risks,
            "automated_risks": automated_risks,
            "risk_adjusted_costs": {
                "manual_cost_with_risk": manual_expected_cost,
                "automated_cost_with_risk": auto_expected_cost,
                "risk_adjusted_savings": manual_expected_cost - auto_expected_cost,
            },
        }

    def create_sensitivity_analysis(
        self, base_scenario: EnterpriseScenario, base_metrics: BusinessMetrics
    ) -> Any:
        """Create sensitivity analysis showing impact of parameter changes."""
        # Parameters to vary
        parameters = {
            "test_cases": [0.5, 0.8, 1.0, 1.5, 2.0],
            "team_size": [0.5, 0.8, 1.0, 1.2, 1.5],
            "complexity_factor": [0.7, 0.85, 1.0, 1.3, 1.8],
            "daily_cost": [0.8, 0.9, 1.0, 1.1, 1.3],
        }

        results = []

        for param_name, multipliers in parameters.items():
            for multiplier in multipliers:
                # Create modified scenario
                modified_scenario = EnterpriseScenario(
                    name=f"Sensitivity_{param_name}_{multiplier}",
                    test_cases=int(
                        base_scenario.test_cases
                        * (multiplier if param_name == "test_cases" else 1)
                    ),
                    team_size=int(
                        base_scenario.team_size
                        * (multiplier if param_name == "team_size" else 1)
                    ),
                    complexity_factor=base_scenario.complexity_factor
                    * (multiplier if param_name == "complexity_factor" else 1),
                )

                # Create modified metrics
                modified_metrics = BusinessMetrics(
                    test_cases=base_metrics.test_cases,
                    manual_time_per_test_days=base_metrics.manual_time_per_test_days,
                    daily_cost_usd=int(
                        base_metrics.daily_cost_usd
                        * (multiplier if param_name == "daily_cost" else 1)
                    ),
                    importobot_time_days=base_metrics.importobot_time_days,
                    manual_success_rate=base_metrics.manual_success_rate,
                    importobot_success_rate=base_metrics.importobot_success_rate,
                )

                # Calculate metrics
                scenario_metrics = modified_scenario.calculate_metrics(modified_metrics)

                results.append(
                    {
                        "parameter": param_name,
                        "multiplier": multiplier,
                        "cost_savings": scenario_metrics["cost_savings_usd"],
                        "time_savings": scenario_metrics["time_savings_days"],
                        "roi": scenario_metrics["roi_multiplier"],
                    }
                )

        return pd.DataFrame(results)

    def generate_executive_summary(
        self, scenarios: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate executive summary across all scenarios."""
        total_scenarios = len(scenarios)

        # Aggregate metrics
        total_cost_savings = sum(s["metrics"]["cost_savings_usd"] for s in scenarios)
        avg_time_reduction = np.mean(
            [s["metrics"]["time_reduction_percent"] for s in scenarios]
        )
        avg_roi = np.mean(
            [
                s["metrics"]["roi_multiplier"]
                for s in scenarios
                if s["metrics"]["roi_multiplier"] != float("inf")
            ]
        )

        # Find best and worst case scenarios
        best_savings = max(scenarios, key=lambda s: s["metrics"]["cost_savings_usd"])
        worst_savings = min(scenarios, key=lambda s: s["metrics"]["cost_savings_usd"])

        return {
            "executive_summary": {
                "total_scenarios_analyzed": total_scenarios,
                "aggregate_cost_savings": total_cost_savings,
                "average_time_reduction_percent": avg_time_reduction,
                "average_roi": avg_roi,
                "best_case": {
                    "scenario": best_savings["scenario"].name,
                    "savings": best_savings["metrics"]["cost_savings_usd"],
                },
                "worst_case": {
                    "scenario": worst_savings["scenario"].name,
                    "savings": worst_savings["metrics"]["cost_savings_usd"],
                },
            },
            "strategic_recommendations": [
                "Prioritize automation for high-volume test migration projects",
                "Consider Importobot for projects with tight timelines",
                "Factor in risk reduction benefits for critical applications",
                "Plan for initial learning curve investment in complex scenarios",
            ],
        }


def create_business_case() -> dict[str, Any]:
    """Create a business case with multiple scenarios."""
    modeler = ScenarioModeler()
    base_metrics = BusinessMetrics()

    # Industry scenarios
    industry_scenarios = []
    for industry in IndustryVertical:
        scenario = modeler.create_industry_scenario(
            industry=industry,
            name=f"{industry.value.replace('_', ' ').title()} Migration",
            test_cases=800,
            team_size=10,
            complexity=ProjectComplexity.STANDARD,
        )
        metrics = scenario.calculate_metrics(base_metrics)
        industry_scenarios.append(
            {"scenario": scenario, "metrics": metrics, "industry": industry}
        )

    # Scale scenarios
    scale_scenarios = modeler.model_scale_scenarios(base_metrics)

    # Timeline scenarios
    base_scenario = EnterpriseScenario(
        name="Standard Enterprise", test_cases=800, team_size=10
    )
    timeline_scenarios = modeler.model_timeline_scenarios(base_scenario, base_metrics)

    # Executive summary
    all_scenarios = industry_scenarios + scale_scenarios + timeline_scenarios
    executive_summary = modeler.generate_executive_summary(all_scenarios)

    return {
        "industry_scenarios": industry_scenarios,
        "scale_scenarios": scale_scenarios,
        "timeline_scenarios": timeline_scenarios,
        "executive_summary": executive_summary,
        "total_scenarios": len(all_scenarios),
    }
