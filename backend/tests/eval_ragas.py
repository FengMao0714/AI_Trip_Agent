# ruff: noqa: E402,RUF001,T201
"""RAGAS evaluation for comparing Agent answers with and without RAG.

Run from backend:
    uv run python tests/eval_ragas.py --limit 24
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.rag.embeddings import encode
from app.tools.rag_search import rag_search

DEFAULT_OUTPUT_DIR = Path("tests/results")
DEFAULT_TOP_K = 3
DEFAULT_CONTEXT_CHAR_LIMIT = 900
DEFAULT_RAGAS_TIMEOUT_SECONDS = 300
DEFAULT_RAGAS_MAX_WORKERS = 4
EXPERIMENT_WITH_RAG = "agent_with_rag"
EXPERIMENT_NO_RAG = "agent_without_rag"


@dataclass(frozen=True)
class EvalCase:
    """One RAGAS evaluation question."""

    city: str
    question: str
    expected_answer: str


@dataclass
class GeneratedSample:
    """One generated sample ready for RAGAS."""

    experiment: str
    city: str
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str


EVAL_CASES: list[EvalCase] = [
    EvalCase(
        city="北京",
        question="北京三日历史文化游应该优先安排哪些景点？",
        expected_answer="应优先安排故宫、天安门、颐和园、八达岭或慕田峪长城等历史文化景点，并按城区集中度减少往返。",
    ),
    EvalCase(
        city="北京",
        question="北京适合亲子半日游的文化场馆有哪些？",
        expected_answer="适合亲子的文化场馆包括故宫、国家博物馆、北京天文馆、北京自然博物馆等，需提前预约并控制单次参观时长。",
    ),
    EvalCase(
        city="北京",
        question="北京一日游如何减少跨城交通消耗？",
        expected_answer="应把天安门、故宫、景山、什刹海等中轴线和核心城区景点串联，避免同日往返长城等远郊点位。",
    ),
    EvalCase(
        city="北京",
        question="北京有哪些适合老人慢节奏参观的景点？",
        expected_answer="颐和园、北海公园、天坛、什刹海等适合慢节奏参观，应减少台阶密集和长距离步行。",
    ),
    EvalCase(
        city="北京",
        question="北京预算有限时餐饮和景点怎么安排？",
        expected_answer="预算有限可选择门票性价比较高的公园和博物馆，餐饮以胡同小吃、老字号简餐和商圈平价餐厅为主。",
    ),
    EvalCase(
        city="北京",
        question="北京两天行程是否适合同时安排故宫和长城？",
        expected_answer="两天可以安排故宫和长城，但建议分两天处理，故宫搭配城区景点，长城单独留出半天到一天。",
    ),
    EvalCase(
        city="北京",
        question="北京雨天旅行有哪些室内备选？",
        expected_answer="雨天可优先安排国家博物馆、首都博物馆、商圈、剧场和预约制展馆，减少户外公园和长城行程。",
    ),
    EvalCase(
        city="北京",
        question="北京夜间适合安排哪些轻量活动？",
        expected_answer="夜间可安排什刹海、前门大街、王府井、三里屯或剧场演出，避免安排需要长途通勤的远郊景点。",
    ),
    EvalCase(
        city="成都",
        question="成都三日休闲美食游怎么规划核心区域？",
        expected_answer="成都三日可围绕宽窄巷子、锦里、武侯祠、人民公园、太古里和熊猫基地规划，并穿插火锅、川菜和茶馆体验。",
    ),
    EvalCase(
        city="成都",
        question="成都适合第一次来的游客安排哪些代表性景点？",
        expected_answer="第一次到成都可安排熊猫基地、武侯祠、锦里、宽窄巷子、杜甫草堂和人民公园，兼顾文化与休闲。",
    ),
    EvalCase(
        city="成都",
        question="成都带老人旅行怎样降低疲劳？",
        expected_answer="带老人应减少连续排队和远距离换乘，选择人民公园、杜甫草堂、宽窄巷子等节奏较慢的点位并安排午休。",
    ),
    EvalCase(
        city="成都",
        question="成都亲子游是否应该安排熊猫基地？",
        expected_answer="亲子游适合安排熊猫基地，建议上午前往、提前预约，并与下午轻松的市区活动搭配。",
    ),
    EvalCase(
        city="成都",
        question="成都一天内如何安排茶馆和川菜体验？",
        expected_answer="可上午游览市区文化景点，中午安排川菜，下午到人民公园茶馆，晚上选择火锅或小吃街。",
    ),
    EvalCase(
        city="成都",
        question="成都雨天有哪些替代行程？",
        expected_answer="成都雨天可安排博物馆、杜甫草堂室内展区、商圈、茶馆和餐饮体验，减少户外步行密集点。",
    ),
    EvalCase(
        city="成都",
        question="成都两日游如何避免景点过散？",
        expected_answer="两日游应一天集中市区历史文化和商圈，另一天安排熊猫基地或近郊，不宜频繁横跨城市。",
    ),
    EvalCase(
        city="成都",
        question="成都预算中等的住宿区域怎么选？",
        expected_answer="预算中等可选春熙路、太古里、宽窄巷子周边或地铁便利区域，兼顾餐饮和景点通勤。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳三日游应该如何结合市区和自然景观？",
        expected_answer="贵阳三日可安排甲秀楼、黔灵山公园、青岩古镇，并视时间加入天河潭或花溪湿地等自然景观。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳第一次旅行有哪些必去点位？",
        expected_answer="第一次到贵阳可优先安排甲秀楼、黔灵山公园、青岩古镇、花溪湿地和本地酸汤鱼等餐饮体验。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳带老人旅行怎么安排更稳妥？",
        expected_answer="带老人应控制山地步行和爬坡，选择甲秀楼、花溪湿地、青岩古镇平缓区域，并预留休息时间。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳有哪些适合慢旅行的市区体验？",
        expected_answer="慢旅行可安排甲秀楼周边、黔灵山公园、咖啡茶饮、夜市和本地餐饮，减少一天内多次远途移动。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳雨天行程如何调整？",
        expected_answer="雨天可减少山地和湿地活动，改去市区餐饮、博物馆、商圈、甲秀楼周边短停或酒店附近体验。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳预算有限时如何吃住行？",
        expected_answer="预算有限可选择地铁或公交便利区域住宿，餐饮以本地小吃和酸汤鱼平价店为主，景点以市区低门票点位为主。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳两日游是否适合加入青岩古镇？",
        expected_answer="两日游可以加入青岩古镇，但应与花溪方向合并安排，另一天留给甲秀楼和黔灵山等市区点位。",
    ),
    EvalCase(
        city="贵阳",
        question="贵阳夜间适合安排哪些活动？",
        expected_answer="夜间适合安排甲秀楼夜景、青云市集、二七路小吃街或商圈餐饮，注意雨天和返程交通。",
    ),
]


class LocalBgeEmbeddings:
    """LangChain-compatible embeddings backed by the app BGE encoder."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = encode(texts)
        return vectors if isinstance(vectors[0], list) else [vectors]  # type: ignore[index]

    def embed_query(self, text: str) -> list[float]:
        vector = encode(text)
        if vector and isinstance(vector[0], list):
            return vector[0]  # type: ignore[index,return-value]
        return vector  # type: ignore[return-value]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)


def select_eval_cases(limit: int | None = None) -> list[EvalCase]:
    """Return the evaluation cases, optionally truncated for smoke runs."""
    return EVAL_CASES if limit is None else EVAL_CASES[:limit]


def _truncate_text(text: str, limit: int) -> str:
    """Limit long context strings for stable evaluator latency."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


async def retrieve_contexts(
    case: EvalCase,
    top_k: int = DEFAULT_TOP_K,
    context_char_limit: int = DEFAULT_CONTEXT_CHAR_LIMIT,
) -> list[str]:
    """Retrieve RAG contexts from the app's RAG search tool."""
    results = await rag_search.ainvoke(
        {"query": case.question, "city": case.city, "top_k": top_k}
    )
    contexts: list[str] = []
    for item in results:
        if not isinstance(item, dict) or item.get("error"):
            continue
        title = item.get("title", "")
        content = item.get("content", "")
        if content:
            context = f"{title}: {content}" if title else str(content)
            contexts.append(_truncate_text(context, context_char_limit))
    return contexts


def build_chat_model() -> ChatOpenAI:
    """Build the LLM used to generate answers and judge RAGAS metrics."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required to run live RAGAS eval.")
    return ChatOpenAI(
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        temperature=0,
    )


async def generate_answer(
    llm: ChatOpenAI,
    case: EvalCase,
    contexts: list[str],
    use_rag: bool,
) -> str:
    """Generate one answer for the A/B experiment."""
    if use_rag:
        system = (
            "你是旅行规划 Agent。必须优先依据给定知识库上下文回答，"
            "不要编造上下文之外的具体价格、地址或营业时间。回答控制在150字以内。"
        )
        context_text = "\n\n".join(contexts) if contexts else "无可用知识库上下文。"
        prompt = f"问题：{case.question}\n\n知识库上下文：\n{context_text}"
    else:
        system = (
            "你是旅行规划 Agent。请只根据通用知识回答，不要使用检索上下文，"
            "如果不确定就给出保守建议。回答控制在150字以内。"
        )
        prompt = f"问题：{case.question}"

    response = await llm.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)]
    )
    return str(response.content)


async def build_experiment_samples(
    cases: list[EvalCase],
    llm: ChatOpenAI,
    top_k: int,
    context_char_limit: int = DEFAULT_CONTEXT_CHAR_LIMIT,
) -> list[GeneratedSample]:
    """Generate RAG and no-RAG samples for all cases."""
    samples: list[GeneratedSample] = []
    for index, case in enumerate(cases, start=1):
        print(
            f"[{index}/{len(cases)}] Retrieving contexts: {case.city} {case.question}",
            flush=True,
        )
        contexts = await retrieve_contexts(
            case,
            top_k=top_k,
            context_char_limit=context_char_limit,
        )
        if not contexts:
            contexts = ["无检索上下文。"]

        print(f"[{index}/{len(cases)}] Generating RAG answer", flush=True)
        rag_answer = await generate_answer(llm, case, contexts, use_rag=True)
        print(f"[{index}/{len(cases)}] Generating no-RAG answer", flush=True)
        no_rag_answer = await generate_answer(llm, case, contexts, use_rag=False)

        samples.append(
            GeneratedSample(
                experiment=EXPERIMENT_WITH_RAG,
                city=case.city,
                question=case.question,
                answer=rag_answer,
                contexts=contexts,
                ground_truth=case.expected_answer,
            )
        )
        samples.append(
            GeneratedSample(
                experiment=EXPERIMENT_NO_RAG,
                city=case.city,
                question=case.question,
                answer=no_rag_answer,
                # Evaluate both groups against the same retrieved evidence so
                # faithfulness reflects grounding in the project knowledge base.
                contexts=contexts,
                ground_truth=case.expected_answer,
            )
        )
    return samples


def samples_to_dataset(samples: list[GeneratedSample]) -> Any:
    """Convert generated samples into a Hugging Face Dataset for RAGAS."""
    from datasets import Dataset

    return Dataset.from_dict(
        {
            "question": [sample.question for sample in samples],
            "answer": [sample.answer for sample in samples],
            "contexts": [sample.contexts for sample in samples],
            "ground_truth": [sample.ground_truth for sample in samples],
        }
    )


def run_ragas(
    samples: list[GeneratedSample],
    llm: ChatOpenAI,
    timeout: int = DEFAULT_RAGAS_TIMEOUT_SECONDS,
    max_workers: int = DEFAULT_RAGAS_MAX_WORKERS,
) -> list[dict[str, Any]]:
    """Run RAGAS metrics and return per-sample score records."""
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.run_config import RunConfig

    try:
        from ragas.metrics import AnswerRelevancy, Faithfulness
    except ImportError:
        from ragas.metrics.collections import AnswerRelevancy, Faithfulness

    evaluator_llm = LangchainLLMWrapper(llm)
    embeddings = LangchainEmbeddingsWrapper(LocalBgeEmbeddings())
    metrics = [
        Faithfulness(llm=evaluator_llm),
        AnswerRelevancy(llm=evaluator_llm, embeddings=embeddings),
    ]

    print(f"Running RAGAS metrics for {len(samples)} generated samples", flush=True)
    result = evaluate(
        dataset=samples_to_dataset(samples),
        metrics=metrics,
        run_config=RunConfig(timeout=timeout, max_workers=max_workers),
    )
    score_rows = getattr(result, "scores", None)
    if score_rows is None:
        score_rows = result.to_pandas().to_dict(orient="records")

    records: list[dict[str, Any]] = []
    for sample, scores in zip(samples, score_rows, strict=True):
        record = asdict(sample)
        record["contexts"] = sample.contexts
        record.update(dict(scores))
        records.append(record)
    return records


def summarize_scores(records: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Average numeric RAGAS metrics by experiment."""
    summaries: dict[str, dict[str, float]] = {}
    for experiment in {record["experiment"] for record in records}:
        group = [record for record in records if record["experiment"] == experiment]
        numeric_keys = [
            key for key, value in group[0].items() if _is_finite_number(value)
        ]
        summaries[experiment] = {
            key: round(
                mean(
                    float(row[key]) for row in group if _is_finite_number(row.get(key))
                ),
                4,
            )
            for key in numeric_keys
        }
    return summaries


def _is_finite_number(value: Any) -> bool:
    """Return whether a value is a finite metric number."""
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _json_safe(value: Any) -> Any:
    """Convert NaN/Inf values into JSON-safe nulls."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def build_markdown_report(payload: dict[str, Any]) -> str:
    """Render a compact Markdown comparison report."""
    summaries = payload["summaries"]
    records = payload["records"]
    metric_names = sorted(
        {
            key
            for summary in summaries.values()
            for key, value in summary.items()
            if _is_finite_number(value)
        }
    )

    lines = [
        "# RAGAS Evaluation Report",
        "",
        f"- Generated at: {payload['metadata']['generated_at']}",
        f"- Cases: {payload['metadata']['case_count']}",
        f"- Samples: {len(records)}",
        "",
        "## A/B Summary",
        "",
        "| Experiment | " + " | ".join(metric_names) + " |",
        "| --- | " + " | ".join("---" for _ in metric_names) + " |",
    ]
    for experiment in sorted(summaries):
        values = [
            (
                f"{summaries[experiment][metric]:.4f}"
                if metric in summaries[experiment]
                else "n/a"
            )
            for metric in metric_names
        ]
        lines.append(f"| {experiment} | " + " | ".join(values) + " |")

    lines.extend(["", "## Per-City Sample Counts", ""])
    city_counts: dict[str, int] = {}
    for record in records:
        city_counts[record["city"]] = city_counts.get(record["city"], 0) + 1
    lines.append("| City | Samples |")
    lines.append("| --- | --- |")
    for city, count in sorted(city_counts.items()):
        lines.append(f"| {city} | {count} |")

    return "\n".join(lines) + "\n"


def write_outputs(
    records: list[dict[str, Any]],
    output_dir: Path,
    cases: list[EvalCase],
) -> tuple[Path, Path]:
    """Save JSON and Markdown evaluation artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "metadata": {
            "generated_at": datetime.now(UTC).isoformat(),
            "case_count": len(cases),
            "experiments": [EXPERIMENT_WITH_RAG, EXPERIMENT_NO_RAG],
            "metrics": ["faithfulness", "answer_relevancy"],
        },
        "summaries": summarize_scores(records),
        "records": records,
    }
    json_path = output_dir / f"ragas_eval_{timestamp}.json"
    md_path = output_dir / f"ragas_eval_{timestamp}.md"
    payload = _json_safe(payload)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    md_path.write_text(build_markdown_report(payload), encoding="utf-8")
    return json_path, md_path


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Limit eval cases.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="RAG top_k.")
    parser.add_argument(
        "--context-char-limit",
        type=int,
        default=DEFAULT_CONTEXT_CHAR_LIMIT,
        help="Maximum characters kept for each retrieved context.",
    )
    parser.add_argument(
        "--ragas-timeout",
        type=int,
        default=DEFAULT_RAGAS_TIMEOUT_SECONDS,
        help="RAGAS per-job timeout in seconds.",
    )
    parser.add_argument(
        "--ragas-max-workers",
        type=int,
        default=DEFAULT_RAGAS_MAX_WORKERS,
        help="RAGAS evaluator worker concurrency.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for JSON and Markdown artifacts.",
    )
    args = parser.parse_args()

    cases = select_eval_cases(args.limit)
    llm = build_chat_model()
    samples = await build_experiment_samples(
        cases,
        llm=llm,
        top_k=args.top_k,
        context_char_limit=args.context_char_limit,
    )
    records = run_ragas(
        samples,
        llm=llm,
        timeout=args.ragas_timeout,
        max_workers=args.ragas_max_workers,
    )
    json_path, md_path = write_outputs(records, output_dir=args.output_dir, cases=cases)
    print(f"Saved RAGAS JSON: {json_path}")
    print(f"Saved RAGAS Markdown: {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
