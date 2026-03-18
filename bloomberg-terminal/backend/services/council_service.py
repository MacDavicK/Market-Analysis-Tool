from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

from backend.services.openrouter import OpenRouterClient


logger = logging.getLogger("bloomberg_terminal.council")


class CouncilService:
    async def run(self, payload: dict) -> dict:
        openrouter = OpenRouterClient()

        anti_hallucination_rules = (
            "- Never invent, estimate, or fabricate numerical values\n"
            "- Use only the exact figures provided in the market data payload\n"
            "- Return null for any data point not present in the input\n"
            "- Do not frame any analysis as investment advice or recommendations"
        )

        final_disclaimer = (
            "This report is for informational purposes only and does not constitute\n"
            "    investment advice. Always consult a qualified financial advisor before\n"
            "    making investment decisions."
        )

        labels = ["Model A", "Model B", "Model C"]
        random.shuffle(labels)
        model_to_label = dict(zip(openrouter.COUNCIL_MODELS, labels))

        report_date = str(payload.get("report_date", ""))
        market_data = payload.get("market_data", {})
        portfolio = payload.get("portfolio", {})
        watchlist = payload.get("watchlist", {})
        data_quality = payload.get("data_quality", {})

        # Stage 1 system prompt (must only reference figures explicitly present)
        stage1_system_prompt = (
            "You are a financial market analyst providing objective data commentary.\n"
            "You must only reference figures explicitly present in the data provided.\n"
            "Never fabricate values.\n"
            "Never provide investment advice or recommendations.\n"
            "Describe observable market conditions only.\n\n"
            f"ANTI-HALLUCINATION RULES:\n{anti_hallucination_rules}"
        )

        # Stage 1 user prompt (structured commentary)
        stage1_user_prompt = (
            "Analyze the following market data and provide a structured commentary.\n"
            "   Cover: crypto prices and sentiment, Indian market conditions (NIFTY,\n"
            "   Bank NIFTY, VIX), US market (S&P 500), precious metals (gold, silver\n"
            "   in USD and INR), portfolio P&L summary, and watchlist observations.\n"
            "   \n"
            f"   Data: {json.dumps(market_data)}\n"
            f"   Portfolio: {json.dumps(portfolio)}\n"
            f"   Watchlist: {json.dumps(watchlist)}\n"
            "   \n"
            "   Rules:\n"
            "- Only reference values present in the data above\n"
            "- Never use: buy, sell, avoid, entry point, buy zone, stop loss\n"
            "- Use observable terms only: above/below moving average, RSI level,\n"
            "  near support/resistance, volume vs average\n"
            "- Return null for missing data points\n"
            "- End with: This report is for informational purposes only."
        )

        # Stage 1 parallel calls
        stage1_model_message_pairs: list[tuple[str, list[dict[str, Any]]]] = []
        for model in openrouter.COUNCIL_MODELS:
            stage1_model_message_pairs.append(
                (
                    model,
                    [
                        {"role": "system", "content": stage1_system_prompt},
                        {"role": "user", "content": stage1_user_prompt},
                    ],
                )
            )

        stage1_results = await openrouter.complete_parallel(
            stage1_model_message_pairs, temperature=0.2
        )

        council_members: list[dict[str, Any]] = []
        label_to_response: dict[str, str] = {}
        stage1_tokens_used = 0

        for i, model in enumerate(openrouter.COUNCIL_MODELS):
            response_text, tokens_used = stage1_results[i]
            stage1_tokens_used += tokens_used
            label = model_to_label[model]
            label_to_response[label] = response_text
            council_members.append(
                {
                    "model": model,
                    "label": label,
                    "response": response_text,
                    "tokens_used": tokens_used,
                }
            )

        # Stage 2 system prompt (quality reviewer)
        stage2_system_prompt = (
            "You are a financial analysis quality reviewer. You will receive two\n"
            "anonymous market analyses. Evaluate them on: factual accuracy,\n"
            "completeness of coverage, clarity, and absence of speculative language.\n"
            "Do not consider writing style. Be objective.\n\n"
            "ANTI-HALLUCINATION RULES:\n"
            f"{anti_hallucination_rules}\n"
        )

        def parse_ranking_json(content: str) -> tuple[list[str], str]:
            # Attempt strict JSON first, then salvage a JSON object inside the text.
            try:
                parsed = json.loads(content)
                ranking_val = parsed.get("ranking", [])
                critique_val = parsed.get("critique", "")
                ranking = ranking_val if isinstance(ranking_val, list) else []
                ranking = [str(x) for x in ranking]
                critique = critique_val if isinstance(critique_val, str) else ""
                return ranking, critique
            except Exception:
                pass

            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return [], ""

            try:
                parsed = json.loads(content[start : end + 1])
                ranking_val = parsed.get("ranking", [])
                critique_val = parsed.get("critique", "")
                ranking = ranking_val if isinstance(ranking_val, list) else []
                ranking = [str(x) for x in ranking]
                critique = critique_val if isinstance(critique_val, str) else ""
                return ranking, critique
            except Exception:
                # Safe fallback for "JSON" returned with single quotes.
                # This does not execute code; it only normalizes quotes for parsing.
                try:
                    normalized = content[start : end + 1].replace("'", '"')
                    parsed = json.loads(normalized)
                    ranking_val = parsed.get("ranking", [])
                    critique_val = parsed.get("critique", "")
                    ranking = ranking_val if isinstance(ranking_val, list) else []
                    ranking = [str(x) for x in ranking]
                    critique = critique_val if isinstance(critique_val, str) else ""
                    return ranking, critique
                except Exception:
                    return [], ""

        async def stage2_call(reviewer_model: str) -> tuple[dict[str, Any], int]:
            reviewer_label = model_to_label[reviewer_model]
            other_labels = [l for l in labels if l != reviewer_label]

            model_x_label, model_x_response = other_labels[0], label_to_response[other_labels[0]]
            model_y_label, model_y_response = other_labels[1], label_to_response[other_labels[1]]

            stage2_user_prompt = (
                "Rank the following two analyses from best to worst and explain\n"
                "   your reasoning in 2-3 sentences per analysis.\n"
                "\n"
                f"   {model_x_label} analysis:\n{model_x_response}\n"
                f"   {model_y_label} analysis:\n{model_y_response}\n"
                "\n"
                "   Respond as JSON:\n"
                "{\n"
                f"     'ranking': ['{model_x_label}', '{model_y_label}'],\n"
                "     'critique': 'your reasoning'\n"
                "   }"
            )

            stage2_messages = [
                {"role": "system", "content": stage2_system_prompt},
                {"role": "user", "content": stage2_user_prompt},
            ]

            response_text, tokens_used = await openrouter.complete(
                model=reviewer_model, messages=stage2_messages, temperature=0.2
            )

            try:
                ranking, critique = parse_ranking_json(response_text)
            except Exception:
                ranking, critique = [], ""

            if not ranking and not critique:
                logger.warning("Stage 2 JSON parsing failed reviewer=%s", reviewer_label)

            return (
                {
                    "reviewer_label": reviewer_label,
                    "ranking": ranking,
                    "critique": critique,
                },
                tokens_used,
            )

        # Stage 2 calls (3 reviewers concurrently)
        stage2_calls = [stage2_call(model) for model in openrouter.COUNCIL_MODELS]
        stage2_results = await asyncio.gather(*stage2_calls)

        peer_reviews: list[dict[str, Any]] = []
        stage2_tokens_used = 0
        for peer_review, tokens_used in stage2_results:
            peer_reviews.append(peer_review)
            stage2_tokens_used += int(tokens_used)

        # Stage 3 — Chairman synthesis
        council_responses = {
            "Model A": label_to_response["Model A"],
            "Model B": label_to_response["Model B"],
            "Model C": label_to_response["Model C"],
        }

        stage3_system_prompt = (
            "You are the chairman of a financial analysis council. You will receive\n"
            "three independent market analyses and their peer review rankings.\n"
            "Your role is to synthesize the strongest elements of each into a single\n"
            "definitive report. You must:\n"
            "- Only include claims supported by at least two of the three analyses\n"
            "- Resolve contradictions by deferring to the majority view\n"
            "- Never add information not present in the source analyses\n"
            "- Never provide investment advice or recommendations\n\n"
            f"ANTI-HALLUCINATION RULES:\n{anti_hallucination_rules}"
        )

        peer_reviews_text = json.dumps(peer_reviews)

        stage3_user_prompt = (
            "Synthesize these three analyses into one comprehensive market report.\n"
            "\n"
            f"Analysis A: {council_responses['Model A']}\n"
            f"Analysis B: {council_responses['Model B']}\n"
            f"Analysis C: {council_responses['Model C']}\n"
            "\n"
            "Peer review rankings:\n"
            f"{peer_reviews_text}\n"
            "\n"
            f"Report date: {report_date}\n"
            "\n"
            "Structure your report as:\n"
            "1. Market Overview\n"
            "2. Crypto Markets\n"
            "3. Indian Markets\n"
            "4. US Markets\n"
            "5. Precious Metals\n"
            "6. Portfolio Summary\n"
            "7. Watchlist Observations\n"
            "8. Key Observations (3-5 bullet points, factual only)\n"
            "\n"
            "End with this disclaimer verbatim:\n"
            f"'{final_disclaimer}'"
        )

        chairman_response, stage3_tokens_used = await openrouter.complete(
            model=openrouter.CHAIRMAN_MODEL,
            messages=[
                {"role": "system", "content": stage3_system_prompt},
                {"role": "user", "content": stage3_user_prompt},
            ],
            temperature=0.2,
        )

        total_tokens_used = stage1_tokens_used + stage2_tokens_used + stage3_tokens_used
        logger.info(
            "Council tokens used: stage1=%s stage2=%s stage3=%s total=%s",
            stage1_tokens_used,
            stage2_tokens_used,
            stage3_tokens_used,
            total_tokens_used,
        )

        report_text = chairman_response.strip()
        if final_disclaimer not in report_text:
            report_text = f"{report_text}\n{final_disclaimer}"

        return {
            "report": report_text,
            "disclaimer": final_disclaimer,
            "council_members": council_members,
            "peer_reviews": peer_reviews,
            "chairman_model": openrouter.CHAIRMAN_MODEL,
            "stages_completed": 3,
            "total_tokens_used": total_tokens_used,
            "report_date": report_date,
        }

