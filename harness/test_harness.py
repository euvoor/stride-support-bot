import json
import sys
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from target import ask, wake_up

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from stride.help_center import DOCS  # the real store policy

dataset = EvaluationDataset(goldens=[
    Golden(input=g["input"], expected_output=g["expected_output"], context=DOCS)
    for g in json.loads((HERE / "goldens.json").read_text())
])

policy_correct = GEval(
    name="Policy correct",
    criteria=(
        "The answer gives the same decision as the expected "
        "output. Any yes or no, number, or time window in "
        "the answer matches the store policy in the context."
    ),
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
        SingleTurnParams.CONTEXT,
    ],
    threshold=0.7,
)

stays_in_docs = GEval(
    name="Stays in docs",
    criteria=(
        "Every fact in the answer comes from the retrieval "
        "context. If the retrieval context does not answer "
        "the question, the answer says so and offers a "
        "human agent."
    ),
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=0.7,
)

metrics = [
    AnswerRelevancyMetric(threshold=0.7),
    FaithfulnessMetric(threshold=0.7),
    policy_correct,
    stays_in_docs,
]

wake_up()


@pytest.mark.parametrize("golden", dataset.goldens)
def test_support_bot(golden):
    answer, sources = ask(golden.input)
    test_case = LLMTestCase(
        input=golden.input,
        actual_output=answer,
        expected_output=golden.expected_output,
        context=golden.context,
        retrieval_context=sources,
    )
    assert_test(test_case, metrics)
