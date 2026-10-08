"""RAGAS: evaluate grounding against contexts actually retrieved by the agent."""

import asyncio
import os

import pytest

from evals.adk_client import ask

pytestmark = pytest.mark.live


@pytest.mark.parametrize("question", [
    "When and where does registration open?",
    "What is the ticket refund policy?",
])
def test_retrieved_context_faithfulness(question):
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics.collections import Faithfulness

    result = ask("conference_agent", question)
    assert result["contexts"], "RAGAS must score actual retrieved evidence"

    async def score():
        async with AsyncOpenAI() as client:
            llm = llm_factory(os.environ.get("JUDGE_MODEL", "gpt-4o-mini"), client=client)
            return await Faithfulness(llm=llm).ascore(
                user_input=question,
                response=result["answer"],
                retrieved_contexts=result["contexts"],
            )

    value = asyncio.run(score()).value
    assert value >= 0.8, f"Faithfulness below threshold: {value}"
