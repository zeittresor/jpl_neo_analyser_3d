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
    verification_task = "5. If a concrete authoritative follow-up source matters for this selected record, mention it in one compact sentence; do not create a generic verification checklist."
    if not include_disclaimer:
        verification_task = "5. Do not add a generic verification checklist. Only mention a concrete authoritative source if it materially helps this selected record."
    return f"""{SYSTEM_NOTE}{limitation_instruction}
Answer strictly in {response_language}.
{mode_instruction}{heuristic_instruction}Use concise Markdown headings and bullets where helpful.
Start the answer with an additional short, readable object article section. This article should be written like a compact science-news/observatory note: fluent prose, generally understandable, interesting comparisons, and a calm scientific tone. Keep it concise and do not replace the technical assessment sections that follow.
Do not create long recurring limitation sections such as "limitations of CAD/local simulation" or generic "verification steps" blocks in the main visible answer. The GUI has localized Usage Notes for that. Keep caveats to one or two directly relevant sentences only when needed.

CAD selected close approach record:
{lines}

Local triage bucket: {bucket}
Bucket reasoning: {bucket_reason}

Raw CAD fields:
{raw_fields}

Additional local context:
{extra_context or 'none'}

Task:
1. Add a short article-style section about the selected object and encounter. Use fluent prose, accessible comparisons, and interesting context. Keep it brief.
2. Give the concise scientific situation assessment as before.
3. Explain whether this looks routine, noteworthy, close, or high-attention based on distance, velocity, object size/uncertainty and time uncertainty.
4. Mention simulation/local-derived-value limits only if they directly affect the selected record, and keep that to one compact sentence rather than a separate limitations section.
{verification_task}
6. Do not sensationalize. Do not infer an official impact probability from this CAD record alone.
7. If table corrections are enabled in the additional local context, put the machine-readable correction block only at the very end using BEGIN_APP_TABLE_CORRECTIONS_JSON / END_APP_TABLE_CORRECTIONS_JSON and never inside a Markdown code fence. If no table correction is needed, emit an empty JSON object inside that block. The GUI hides this block from the displayed text.
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
