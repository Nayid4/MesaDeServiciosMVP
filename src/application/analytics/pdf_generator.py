"""Generador PDF 1.4 puro en Python para reportes ejecutivos RIU-10 (CASAGBI UPC)."""

from __future__ import annotations

from typing import Any, Dict, List


def _pdf_escape(text: str) -> str:
    """Normaliza a Latin-1 seguro y escapa caracteres especiales de cadena PDF."""
    safe = (
        str(text or "")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("—", "-")
        .replace("–", "-")
        .replace("·", "|")
    )
    safe = safe.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _draw_text(x: float, y: float, text: str, *, bold: bool = False, size: int = 10) -> str:
    font = "F2" if bold else "F1"
    return f"BT /{font} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({_pdf_escape(text)}) Tj ET"


def _draw_line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f"{x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S"


def build_riu10_pdf_report(
    *,
    meta: Dict[str, Any],
    kpis: Dict[str, Any],
    tickets: List[Dict[str, Any]],
) -> bytes:
    """Construye un documento PDF 1.4 tabular institucional siguiendo el formato RIU-10."""
    pages_ops: List[List[str]] = []

    def new_page(page_num: int) -> List[str]:
        ops = [
            "0.0 0.408 0.216 RG 1.2 w",
            _draw_line(40, 795, 555, 795),
            "0 0 0 rg",
            _draw_text(40, 804, "UNIVERSIDAD POPULAR DEL CESAR - MESA DE SERVICIOS TIC (CASAGBI)", bold=True, size=11),
            _draw_text(40, 782, f"Formato Oficial RIU-10 | Reporte ITIL v4 (Pagina {page_num})", bold=True, size=9),
        ]
        return ops

    ops = new_page(1)
    y = 762.0

    # Bloque de metadatos RIU-10
    ops.append(_draw_text(40, y, f"Fecha generacion: {meta.get('generated_at', '')}", size=9))
    ops.append(_draw_text(300, y, f"Alcance: {meta.get('scope_label', '')}", size=9))
    y -= 14
    ops.append(_draw_text(40, y, f"Generado por: {meta.get('actor_name', '')} ({meta.get('actor_role', '')})", size=9))
    y -= 14
    ops.append(_draw_text(40, y, f"Filtros aplicados: {meta.get('filters_summary', 'Ninguno')}", size=9))
    y -= 18
    ops.append("0.7 0.7 0.7 RG 0.5 w")
    ops.append(_draw_line(40, y + 6, 555, y + 6))
    ops.append("0 0 0 rg")

    # Resumen KPI
    y -= 10
    ops.append(_draw_text(40, y, "RESUMEN DE INDICADORES CLAVE DE RENDIMIENTO (KPI)", bold=True, size=10))
    y -= 16
    kpi_lines = [
        f"Total tickets en alcance: {kpis.get('total_tickets', 0)}   |   Abiertos: {kpis.get('open_tickets', 0)}   |   Resueltos/Cerrados: {kpis.get('resolved_or_closed', 0)}",
        f"Cumplimiento SLA: {kpis.get('sla_compliance_pct', 0)}%   |   En riesgo >=75%: {kpis.get('at_risk_open_count', 0)}",
        f"Primera respuesta promedio: {kpis.get('avg_first_response_min', 0)} min   |   Resolucion promedio: {kpis.get('avg_resolution_hours', 0)} h",
        f"Satisfaccion CSAT: {kpis.get('avg_csat', 0)} / 5   |   Tasa de reapertura: {kpis.get('reopen_rate_pct', 0)}%",
    ]
    for line in kpi_lines:
        ops.append(_draw_text(44, y, line, size=9))
        y -= 13

    y -= 10
    ops.append(_draw_text(40, y, "DETALLE DE SOLICITUDES E INCIDENCIAS (ALCANCE DEL ROL)", bold=True, size=10))
    y -= 15

    def add_table_header(target_ops: List[str], yy: float) -> float:
        target_ops.append(_draw_text(40, yy, "Radicado", bold=True, size=8))
        target_ops.append(_draw_text(135, yy, "Servicio", bold=True, size=8))
        target_ops.append(_draw_text(310, yy, "Sede", bold=True, size=8))
        target_ops.append(_draw_text(415, yy, "Prio", bold=True, size=8))
        target_ops.append(_draw_text(475, yy, "Estado", bold=True, size=8))
        target_ops.append("0.4 0.4 0.4 RG 0.5 w")
        target_ops.append(_draw_line(40, yy - 4, 555, yy - 4))
        target_ops.append("0 0 0 rg")
        return yy - 15

    y = add_table_header(ops, y)

    if not tickets:
        ops.append(_draw_text(40, y, "No hay tickets registrados para los filtros seleccionados.", size=9))
    else:
        for t in tickets[:150]:
            if y < 65:
                pages_ops.append(ops)
                ops = new_page(len(pages_ops) + 1)
                y = 755.0
                y = add_table_header(ops, y)

            code = str(t.get("ticket_number", ""))[:19]
            svc = str(t.get("service_name", ""))[:32]
            sede = str(t.get("sede", ""))[:20]
            prio = str(t.get("priority", ""))[:10]
            status = str(t.get("status", ""))[:14]

            ops.append(_draw_text(40, y, code, size=8))
            ops.append(_draw_text(135, y, svc, size=8))
            ops.append(_draw_text(310, y, sede, size=8))
            ops.append(_draw_text(415, y, prio, size=8))
            ops.append(_draw_text(475, y, status, size=8))
            y -= 13

    pages_ops.append(ops)

    # Ensamblar objetos PDF (1: Catalog, 2: Pages, 3: Helvetica, 4: Helvetica-Bold, luego pares Page + Stream)
    objects: List[bytes] = []
    num_pages = len(pages_ops)
    page_obj_nums = [5 + i * 2 for i in range(num_pages)]

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids_str = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects.append(f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    for idx, page_cmds in enumerate(pages_ops):
        p_num = 5 + idx * 2
        c_num = p_num + 1
        stream_bytes = ("\n".join(page_cmds) + "\n").encode("latin-1", "replace")
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {c_num} 0 R >>"
        ).encode("ascii")
        content_obj = (
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"endstream"
        )
        objects.append(page_dict)
        objects.append(content_obj)

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = [0]
    for obj_idx, obj_body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{obj_idx} 0 obj\n".encode("ascii"))
        out.extend(obj_body)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(out)
