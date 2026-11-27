"""Allowlisted, read-only access to the repository's skill guides."""

from __future__ import annotations

from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1] / "SKILLS"
SKILL_FILES = {
    "Compare_Periods": "Narrative/Compare_Periods.md",
    "Detect_Anomalies": "Narrative/Detect_Anomalies.md",
    "Generate_Narrative": "Narrative/Generate_Narrative.md",
    "Highlight_Findings": "Narrative/Highlight_Findings.md",
    "Human_Review_Flag": "Narrative/Human_Review_Flag.md",
    "Verify_Numbers": "Narrative/Verify_Numbers.md",
    "Build_Dashboard_Payload": "Dashboard_Outputs/Build_Dashboard_Payload.md",
    "Select_Template": "Dashboard_Outputs/Select_Template.md",
    "Render_PDF": "Dashboard_Outputs/Render_PDF.md",
    "Render_Excel": "Dashboard_Outputs/Render_Excel.md",
    "Publish_Report": "Dashboard_Outputs/Publish_Report.md",
    "Download_CSV": "Recopilation/Download_CSV.md",
    "Fetch_From_Storage": "Recopilation/Fetch_From_Storage.md",
    "Schedule_Logs": "Recopilation/Schedule_Logs.md",
    "Validate_CSV_schema": "Recopilation/Validate_CSV_schema.md",
    "Validate_Data_Quality": "Recopilation/Validate_Data_Quality..md",
}


def available_skill_guides() -> list[dict[str, str]]:
    guides = []
    for name, relative_path in SKILL_FILES.items():
        path = SKILL_ROOT / relative_path
        if not path.is_file():
            status = "missing"
        elif path.stat().st_size == 0:
            status = "empty"
        else:
            status = "guide_only"
        guides.append({"name": name, "status": status})
    return guides


def read_skill_guide(name: str, section: str | None = None) -> dict[str, object]:
    if name not in SKILL_FILES:
        raise ValueError(f"Skill desconocido: {name}")
    path = (SKILL_ROOT / SKILL_FILES[name]).resolve()
    if not path.is_relative_to(SKILL_ROOT.resolve()):
        raise ValueError("La guía está fuera del directorio de skills.")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"No se pudo leer la guía {name}: {error}") from error
    if not content.strip():
        raise ValueError(f"La guía {name} está vacía y no se puede utilizar.")

    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in content.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            if current in sections:
                raise ValueError(f"La guía {name} tiene secciones duplicadas: {current}")
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    if not sections:
        raise ValueError(f"La guía {name} no contiene secciones utilizables.")
    if section is not None and section not in sections:
        raise ValueError(f"Sección desconocida para {name}: {section}")

    selected = (
        [section] if section is not None
        else [heading for heading in ("Purpose", "Required inputs", "Forbidden behavior") if heading in sections]
    )
    return {
        "skill": name,
        "status": "guide_only",
        "notice": (
            "La guía no ejecuta acciones ni verifica datos. Usa solo herramientas "
            "disponibles y comunica las capacidades que no están implementadas."
        ),
        "sections_available": list(sections),
        "content": {heading: "\n".join(sections[heading]).strip() for heading in selected},
    }
