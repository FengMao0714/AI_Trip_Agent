"""Tests for the RAGAS evaluation helper script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_eval_module() -> Any:
    module_path = Path(__file__).with_name("eval_ragas.py")
    spec = importlib.util.spec_from_file_location("eval_ragas", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


eval_ragas = _load_eval_module()


def test_eval_cases_cover_three_cities() -> None:
    cases = eval_ragas.select_eval_cases()
    cities = {case.city for case in cases}

    assert len(cases) == 24
    assert {"北京", "成都", "贵阳"} <= cities


def test_summarize_scores_groups_experiments() -> None:
    records = [
        {
            "experiment": eval_ragas.EXPERIMENT_WITH_RAG,
            "faithfulness": 0.8,
            "answer_relevancy": 0.7,
        },
        {
            "experiment": eval_ragas.EXPERIMENT_WITH_RAG,
            "faithfulness": 1.0,
            "answer_relevancy": 0.9,
        },
        {
            "experiment": eval_ragas.EXPERIMENT_NO_RAG,
            "faithfulness": 0.4,
            "answer_relevancy": 0.5,
        },
    ]

    summary = eval_ragas.summarize_scores(records)

    assert summary[eval_ragas.EXPERIMENT_WITH_RAG]["faithfulness"] == 0.9
    assert summary[eval_ragas.EXPERIMENT_WITH_RAG]["answer_relevancy"] == 0.8
    assert summary[eval_ragas.EXPERIMENT_NO_RAG]["faithfulness"] == 0.4


def test_markdown_report_contains_ab_summary() -> None:
    payload = {
        "metadata": {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "case_count": 1,
        },
        "summaries": {
            eval_ragas.EXPERIMENT_WITH_RAG: {
                "faithfulness": 0.9,
                "answer_relevancy": 0.8,
            },
            eval_ragas.EXPERIMENT_NO_RAG: {
                "faithfulness": 0.4,
                "answer_relevancy": 0.5,
            },
        },
        "records": [
            {
                "experiment": eval_ragas.EXPERIMENT_WITH_RAG,
                "city": "北京",
            },
            {
                "experiment": eval_ragas.EXPERIMENT_NO_RAG,
                "city": "北京",
            },
        ],
    }

    report = eval_ragas.build_markdown_report(payload)

    assert "# RAGAS Evaluation Report" in report
    assert "| agent_with_rag |" in report
    assert "| 北京 | 2 |" in report
