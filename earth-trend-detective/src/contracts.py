"""Typed contracts between workflow nodes (pydantic)."""

from typing import Literal

from pydantic import BaseModel, Field

# Closed lists: the LLM can only choose among these values.
# They must match the keys used by src/agents/tools.py.
Zone = Literal["napoli", "caserta", "salerno", "avellino", "benevento"]
Variable = Literal["T2M", "PRECTOTCORR"]


class PlanItem(BaseModel):
    """One analysis to run: a NASA POWER variable in a zone of Campania over a period."""

    zone: Zone = Field(
        description="Sampling zone in Campania (southern Italy), named after its main town."
    )
    variable: Variable = Field(
        description="T2M = air temperature at 2 m (degC); PRECTOTCORR = precipitation (mm/day)."
    )
    start_year: int = Field(
        default=1981, ge=1981, le=2024,
        description="First year of the period. Keep the default unless the user asks for a period.",
    )
    end_year: int = Field(
        default=2024, ge=1981, le=2024,
        description="Last year of the period. Keep the default unless the user asks for a period.",
    )


class Plan(BaseModel):
    """What the planner decided to analyse to answer the user's question."""

    out_of_scope: bool = Field(
        default=False,
        description=(
            "True if the question is not about temperature or precipitation trends in "
            "Campania, or asks about places or variables that are not available. "
            "If true, leave items empty."
        ),
    )
    reason: str = Field(
        default="",
        description="One short sentence explaining the decision (used for logs, not shown to the user).",
    )
    # 5 zones x 2 variables = 10 possible analyses at most.
    items: list[PlanItem] = Field(default_factory=list, max_length=10)
