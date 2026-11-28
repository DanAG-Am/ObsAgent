"""Spanish presentation labels; never modify analytical identifiers or values."""

from __future__ import annotations

import re
from typing import Any

from .variable_dictionary import SOURCE_FIELDS


TOOL_LABELS = {
    "detectar_fraude": "Detectar fraude con C4.5",
    "validar_csv_local": "Validar el CSV local",
    "consultar_diccionario": "Consultar diccionario de variables",
    "consultar_skill": "Consultar guía",
    "portfolio_kpis": "Indicadores de cartera",
    "cohort_curve": "Evolución por cosecha",
    "kpis_by_dimension": "Indicadores por dimensión",
    "vintage_comparison": "Comparación de cosechas",
    "segment_ranking": "Clasificación de segmentos",
    "anomaly_candidates": "Posibles anomalías",
}

FIELD_LABELS = {
    "vintage": "Cosecha", "strategy": "Estrategia",
    "strategy_segment": "Segmento de estrategia", "product": "Producto",
    "channel": "Canal", "age_tag": "Grupo de edad", "score_tag": "Grupo de puntuación",
    "mob": "Mes en libros", "accounts": "Cuentas",
    "credit_lines_amount": "Monto de líneas de crédito",
    "enrolled_accounts": "Cuentas con saldo", "over30_accounts": "Cuentas con atraso mayor a 30 días",
    "over30_amount": "Saldo con atraso mayor a 30 días",
    "gross_chargeoff_amount": "Pérdida bruta", "net_chargeoff_amount": "Pérdida neta",
    "recovery_amount": "Monto recuperado", "enrolled_amount": "Saldo inscrito",
    "revenue": "Ingresos", "acquisition_expense": "Gastos de adquisición",
    "variable_ecm_expense": "Gastos variables", "fixed_ecm_expense": "Gastos fijos",
    "total_expense": "Gastos totales",
    "delinquency_rate_amount": "Tasa de morosidad (monto)",
    "delinquency_rate_accounts": "Tasa de morosidad (cuentas)",
    "gross_chargeoff_rate": "Tasa de castigo bruto", "net_chargeoff_rate": "Tasa de castigo neto",
    "recovery_rate": "Tasa de recuperación", "utilization_rate": "Tasa de utilización",
    "operating_margin": "Margen operativo", "operating_margin_rate": "Tasa de margen operativo",
    "efficiency_ratio": "Índice de eficiencia", "acquisition_cost_per_account": "Costo de adquisición por cuenta",
    "filters": "Filtros", "group_by": "Agrupar por", "metric": "Indicador",
    "limit": "Límite", "descending": "Orden descendente", "minimum_accounts": "Mínimo de cuentas",
    "measures": "Medidas", "metrics": "Indicadores", "row_count": "Filas agregadas",
    "baseline_vintage": "Cosecha de referencia", "comparison_vintage": "Cosecha comparada",
    "baseline": "Referencia", "comparison": "Comparación", "metric_delta": "Diferencia de indicadores",
    "anomaly": "Anomalía", "error": "Error", "tool": "Herramienta",
    "arguments": "Argumentos", "result": "Resultado", "tool_results": "Resultados de herramientas",
    "dashboard_context": "Contexto del panel", "builder_used": "Redactor utilizado",
    "translation_used": "Traducción utilizada", "translated_query": "Consulta traducida",
    "dictionary_warning": "Aviso del diccionario", "nombre": "Nombre", "seccion": "Sección",
    "duration_ms": "Duración (ms)", "timings_ms": "Tiempos (ms)",
    "researcher": "Investigador", "builder": "Redactor",
    "variable": "Variable", "variable_fuente": "Variable de origen",
    "descripcion": "Descripción", "aviso": "Aviso", "skill": "Guía",
    "status": "Estado", "notice": "Aviso", "sections_available": "Secciones disponibles",
    "content": "Contenido", "herramientas_disponibles": "Herramientas disponibles",
    "archivo": "Archivo", "filas": "Filas", "filas_validas": "Filas válidas",
    "filas_rechazadas": "Filas rechazadas", "columnas_adicionales": "Columnas adicionales",
    "incidencias": "Incidencias", "tolerancia_conciliacion": "Tolerancia de conciliación",
    "advertencias": "Advertencias",
    "duplicados_exactos": "Filas duplicadas exactas",
    "cosechas_con_huecos_internos": "Cosechas con meses intermedios faltantes",
    "cobertura": "Cobertura", "primer_mob": "Primer mes",
    "ultimo_mob": "Último mes", "intervalos_faltantes": "Intervalos intermedios faltantes",
    "desde": "Desde", "hasta": "Hasta",
    "tipo": "Tipo", "metodo": "Método", "unidad_tasa": "Unidad de tasa",
    "modelo": "Modelo", "transacciones_analizadas": "Transacciones analizadas",
    "transaccion": "Transacción", "risk_level": "Nivel de riesgo",
    "fraud_probability": "Puntuación del modelo", "threshold": "Umbral",
    "risk_reasons": "Indicadores adicionales", "explanation": "Explicación",
    "decision_path": "Ruta de decisión", "prediction": "Clasificación",
    "feature": "Variable", "value": "Valor", "condition": "Condición",
    "branch": "Rama",
    "q1": "Primer cuartil", "q3": "Tercer cuartil",
    "limite_inferior": "Límite inferior", "limite_superior": "Límite superior",
    "resultados": "Resultados", "canal": "Canal", "tasa": "Tasa",
    "transacciones_simuladas": "Transacciones simuladas",
    "incidentes_simulados": "Incidentes simulados", "valor_atipico": "Valor atípico",
    "numero_de_campos_incorrecto": "Número de campos incorrecto",
    "caracter_nulo": "Carácter nulo", "texto_requerido_vacio": "Texto requerido vacío",
    "numero_invalido": "Número inválido", "entero_invalido": "Entero inválido",
    "numero_negativo_o_no_finito": "Número negativo o no finito",
    "cosecha_invalida": "Cosecha inválida", "perdida_neta_no_conciliada": "Pérdida neta no conciliada",
    "gastos_no_conciliados": "Gastos no conciliados",
    "gasto_adquisicion_fuera_de_mob_cero": "Gasto de adquisición fuera del mes cero",
    "$gte": "Desde (inclusive)", "$lte": "Hasta (inclusive)",
    "$gt": "Mayor que", "$lt": "Menor que",
}

SKILL_LABELS = {
    "Detect_Fraud": "Detectar fraude",
    "Compare_Periods": "Comparar periodos", "Detect_Anomalies": "Detectar anomalías",
    "Generate_Narrative": "Generar narrativa", "Highlight_Findings": "Destacar hallazgos",
    "Verify_Numbers": "Verificar cifras",
    "Build_Dashboard_Payload": "Preparar datos del panel", "Select_Template": "Seleccionar plantilla",
    "Render_PDF": "Generar PDF", "Render_Excel": "Generar Excel",
    "Publish_Report": "Publicar reporte", "Download_CSV": "Descargar CSV",
    "Schedule_Logs": "Programar registros",
    "Validate_CSV_schema": "Validar estructura del CSV", "Validate_Data_Quality": "Validar calidad de datos",
}


def display_answer(text: str) -> str:
    """Translate known technical identifiers without changing data values."""
    identifiers = {**FIELD_LABELS, **TOOL_LABELS, **SKILL_LABELS}
    identifiers.update({
        source: FIELD_LABELS[internal]
        for internal, source in SOURCE_FIELDS.items()
        if internal in FIELD_LABELS
    })

    def parenthetical(match: re.Match[str]) -> str:
        name = match.group(1).strip("`")
        if name == "MOB":
            return match.group(0)
        if name in {"baseline", "comparison"}:
            return f" ({identifiers[name].lower()})"
        if name in identifiers:
            label = identifiers[name]
            if match.string[:match.start()].casefold().endswith(label.casefold()):
                return ""
            return f" ({label.lower()})"
        return match.group(0)

    text = re.sub(r"\s+\((`?[A-Za-z][A-Za-z0-9_]*`?)\)", parenthetical, text)

    def inline_code(match: re.Match[str]) -> str:
        name = match.group(1)
        return identifiers.get(name, match.group(0))

    return re.sub(r"`([A-Za-z][A-Za-z0-9_]*)`", inline_code, text)


def display_trace_value(value: Any, parent: str = "") -> Any:
    if isinstance(value, dict):
        return {
            FIELD_LABELS.get(key, key): display_trace_value(item, key)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [display_trace_value(item, parent) for item in value]
    if isinstance(value, str):
        if parent in {"group_by", "metric"}:
            return FIELD_LABELS.get(value, value)
        if parent == "tool":
            return TOOL_LABELS.get(value, value)
        if parent in {"nombre", "skill"}:
            return SKILL_LABELS.get(value, value)
        if parent == "anomaly":
            return {"low": "Baja", "high": "Alta"}.get(value, value)
        if parent == "status":
            return {"guide_only": "Solo guía", "empty": "Vacía", "missing": "No disponible",
                    "rejected": "Rechazado", "issues_found": "Se encontraron incidencias",
                    "checks_completed": "Comprobaciones completadas"}.get(value, value)
        if parent == "tipo" and value == "deteccion_fraude_c45":
            return "Detección C4.5"
        if parent == "risk_level":
            return {
                "Fraudulent": "Fraudulenta",
                "Suspicious": "Sospechosa",
                "Legitimate": "Legítima",
            }.get(value, value)
    return value
