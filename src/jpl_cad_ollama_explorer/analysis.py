# source: https://github.com/zeittresor
from __future__ import annotations

from .cad_models import CadRecord


SYSTEM_NOTE = """You are analyzing NASA/JPL SBDB Close Approach Data (CAD).
Be careful and scientifically conservative. Do not claim impact risk unless the data explicitly supports it.
Explain CAD values in plain language. Distinguish official data from local heuristic triage and from approximate simulation.
"""

LIMITATION_NOTE = """Mention that CAD is a close-approach summary and not a complete orbit/covariance solution.
"""

NO_REPEATED_LIMITATION_NOTE = """The user has disabled repeated educational/statistical disclaimer text. Stay scientifically conservative, but do not add a broad generic disclaimer section unless it is directly necessary to avoid a wrong or unsafe interpretation.
"""


def build_ollama_prompt(
    record: CadRecord,
    extra_context: str = "",
    response_language: str = "English",
    include_disclaimer: bool = True,
    assessment_mode: str = "assessment",
    include_heuristic_notes: bool = False,
) -> str:
    bucket, bucket_reason = record.risk_bucket()
    lines = "\n".join(f"- {line}" for line in record.summary_lines())
    raw_fields = "\n".join(f"  {k}: {v}" for k, v in record.raw.items())
    limitation_instruction = LIMITATION_NOTE if include_disclaimer else NO_REPEATED_LIMITATION_NOTE
    if assessment_mode == "facts":
        mode_instruction = "Use a data-focused style: explain directly supported CAD fields and visible computed columns, but do not add speculative risk estimates unless explicitly requested.\n"
    elif assessment_mode == "exploratory":
        mode_instruction = "Exploratory mode is enabled: you may provide cautious scenario-based or what-if estimates, but every estimate must state its assumptions and must not be presented as an official impact probability.\n"
    else:
        mode_instruction = "Scientific assessment mode is enabled: you may provide careful interpretation from CAD values and visible local-computed columns; avoid sensationalism and do not invent official probabilities.\n"
    heuristic_instruction = (
        "The user wants explicit mentions when values are local-computed or heuristic where it helps clarity.\n"
        if include_heuristic_notes
        else "Do not repeatedly explain that local triage/scores are heuristics; keep caveats terse unless essential to avoid a wrong conclusion.\n"
    )
    verification_task = "4. List concrete verification steps if someone wanted authoritative risk assessment."
    if not include_disclaimer:
        verification_task = "4. Only mention verification steps if they materially help answer this specific record; avoid repeated generic disclaimers."
    return f"""{SYSTEM_NOTE}{limitation_instruction}
Answer strictly in {response_language}.
{mode_instruction}{heuristic_instruction}Use concise Markdown headings and bullets where helpful.

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
{verification_task}
5. Do not sensationalize. Do not infer an impact probability from this CAD record alone.
"""


def fallback_analysis(record: CadRecord, language: str = "en", include_disclaimer: bool = True, extra_context: str = "", include_heuristic_notes: bool = False) -> str:
    bucket, reason = record.risk_bucket()
    lines = "\n".join(record.summary_lines())
    context_block = f"\n\n**Change context:**\n{extra_context}" if extra_context.strip() else ""
    if language == "de":
        heading = "### Lokale Einschätzung ohne Ollama\n\n" if not include_heuristic_notes else "### Lokale heuristische Einschätzung ohne Ollama\n\n"
        text = (
            heading
            + f"{lines}{context_block}\n\n"
            f"**Kurzfazit:** {bucket}. {reason}"
        )
        if include_disclaimer:
            text += (
                "\n\n**Wichtig:** Dies ist keine offizielle Gefahreneinschätzung. Die CAD-API liefert Close-Approach-Zusammenfassungen. "
                "Für echte Bahnbestimmung, Kovarianzen und Risikobewertung sind offizielle JPL/CNEOS-Seiten, Horizons/SPICE-Daten und aktuelle Beobachtungen maßgeblich."
            )
        return text
    if language == "fr":
        heading = "### Évaluation locale sans Ollama\n\n" if not include_heuristic_notes else "### Évaluation heuristique locale sans Ollama\n\n"
        text = (
            heading
            + f"{lines}{context_block}\n\n"
            f"**Conclusion rapide:** {bucket}. {reason}"
        )
        if include_disclaimer:
            text += (
                "\n\n**Important:** Ceci n'est pas une évaluation officielle du danger. L'API CAD fournit des résumés de rapprochement. "
                "Pour la détermination orbitale, les covariances et l'évaluation du risque, il faut consulter les pages officielles JPL/CNEOS, les données Horizons/SPICE et les observations récentes."
            )
        return text
    if language == "ru":
        heading = "### Локальная оценка без Ollama\n\n" if not include_heuristic_notes else "### Локальная эвристическая оценка без Ollama\n\n"
        text = (
            heading
            + f"{lines}{context_block}\n\n"
            f"**Краткий вывод:** {bucket}. {reason}"
        )
        if include_disclaimer:
            text += (
                "\n\n**Важно:** Это не официальная оценка опасности. CAD API предоставляет сводки о сближениях. "
                "Для реального определения орбиты, ковариаций и оценки риска нужны официальные страницы JPL/CNEOS, данные Horizons/SPICE и актуальные наблюдения."
            )
        return text
    heading = "### Local assessment without Ollama\n\n" if not include_heuristic_notes else "### Local heuristic assessment without Ollama\n\n"
    text = (
        heading
        + f"{lines}{context_block}\n\n"
        f"**Quick conclusion:** {bucket}. {reason}"
    )
    if include_disclaimer:
        text += (
            "\n\n**Important:** This is not an official hazard assessment. The CAD API provides close-approach summaries. "
            "For real orbit determination, covariance information, and risk assessment, official JPL/CNEOS pages, Horizons/SPICE data, and current observations are authoritative."
        )
    return text
