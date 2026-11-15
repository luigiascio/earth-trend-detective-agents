"""Typed contracts between workflow nodes (pydantic)."""

from typing import Literal

from pydantic import BaseModel, Field

# Closed lists: the LLM can only choose among these values.
# They must match the keys used by src/agents/tools.py.
Zone = Literal["napoli", "caserta", "salerno", "avellino", "benevento"]
Variable = Literal["T2M", "PRECTOTCORR"]


class PlanItem(BaseModel):
    """One analysis to run: a NASA POWER variable in a zone of Campania over a period.

    T2M is air temperature at 2 m, PRECTOTCORR is corrected precipitation.
    """

    zone: Zone
    variable: Variable
    start_year: int = Field(default=1981, ge=1981, le=2024)
    end_year: int = Field(default=2024, ge=1981, le=2024)


class Plan(BaseModel):
    """What the planner decided to analyse to answer the user's question."""

    # 5 zones x 2 variables = 10 possible analyses at most.
    items: list[PlanItem] = Field(min_length=1, max_length=10)
