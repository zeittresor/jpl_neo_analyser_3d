# source: https://github.com/zeittresor
from __future__ import annotations

from .cad_models import CadRecord


SYSTEM_NOTE = """You are analyzing NASA/JPL SBDB Close Approach Data (CAD).
Be careful and scientifically conservative. Do not claim impact risk unless the data explicitly supports it.
Explain CAD values in plain language. Distinguish official data from local heuristic triage and from approximate simulation.
Mention that CAD is a close-approach summary and not a complete orbit/covariance solution.
"""


def build_ollama_prompt(record: CadRecord, extra_context: str = "", response_language: str = "English") -> str:
    bucket, bucket_reason = record.risk_bucket()
    lines = "\n".join(f"- {line}" for line in record.summary_lines())
    raw_fields = "\n".join(f"  {k}: {v}" for k, v in record.raw.items())
    return f"""{SYSTEM_NOTE}
Answer strictly in {response_language}.
Use concise Markdown headings and bullets where helpful.

CAD selected close approach record:
{lines}

Local triage bucket: {bucket}
Bucket reasoning: {bucket_reason}

Raw CAD fields:
{raw_fields}

Additional local context:
{extra_context or 'none'}

Task:
1. Give a concise human-readable situation assessment.
2. Explain whether this looks routine, noteworthy, close, or high-attention based on distance, velocity, object size/uncertainty and time uncertainty.
3. Explain what the local simulation can and cannot show.
4. List concrete verification steps if someone wanted authoritative risk assessment.
5. Do not sensationalize. Do not infer an impact probability from this CAD record alone.
"""


def fallback_analysis(record: CadRecord, language: str = "en") -> str:
    bucket, reason = record.risk_bucket()
    lines = "\n".join(record.summary_lines())
    if language == "de":
        return (
            "### Lokale heuristische Einschätzung ohne Ollama\n\n"
            f"{lines}\n\n"
            f"**Kurzfazit:** {bucket}. {reason}\n\n"
            "**Wichtig:** Dies ist keine offizielle Gefahreneinschätzung. Die CAD-API liefert Close-Approach-Zusammenfassungen. "
            "Für echte Bahnbestimmung, Kovarianzen und Risikobewertung sind offizielle JPL/CNEOS-Seiten, Horizons/SPICE-Daten und aktuelle Beobachtungen maßgeblich."
        )
    if language == "fr":
        return (
            "### Évaluation heuristique locale sans Ollama\n\n"
            f"{lines}\n\n"
            f"**Conclusion rapide:** {bucket}. {reason}\n\n"
            "**Important:** Ceci n'est pas une évaluation officielle du danger. L'API CAD fournit des résumés de rapprochement. "
            "Pour la détermination orbitale, les covariances et l'évaluation du risque, il faut consulter les pages officielles JPL/CNEOS, les données Horizons/SPICE et les observations récentes."
        )
    if language == "ru":
        return (
            "### Локальная эвристическая оценка без Ollama\n\n"
            f"{lines}\n\n"
            f"**Краткий вывод:** {bucket}. {reason}\n\n"
            "**Важно:** Это не официальная оценка опасности. CAD API предоставляет сводки о сближениях. "
            "Для реального определения орбиты, ковариаций и оценки риска нужны официальные страницы JPL/CNEOS, данные Horizons/SPICE и актуальные наблюдения."
        )
    return (
        "### Local heuristic assessment without Ollama\n\n"
        f"{lines}\n\n"
        f"**Quick conclusion:** {bucket}. {reason}\n\n"
        "**Important:** This is not an official hazard assessment. The CAD API provides close-approach summaries. "
        "For real orbit determination, covariance information, and risk assessment, official JPL/CNEOS pages, Horizons/SPICE data, and current observations are authoritative."
    )
