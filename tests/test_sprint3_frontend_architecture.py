"""Pruebas obligatorias de Sprint 3: Screaming Architecture JS, helpers/guardas en Node, CSV/PDF RIU-10 y WCAG."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.infrastructure.composition import reset_runtime_dependencies
from src.infrastructure.persistence.database import dispose_engines, init_database
from src.main import create_app


@pytest.fixture
def sprint3_client(tmp_path, monkeypatch):
    db_file = tmp_path / "sprint3_reports.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    monkeypatch.setenv("DEMO_MODE", "true")
    reset_runtime_dependencies()
    dispose_engines()
    init_database(db_file, seed=True)

    app = create_app()
    with TestClient(app) as client:
        yield client

    dispose_engines()
    reset_runtime_dependencies()


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"email": email, "demo_mode": True})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_screaming_architecture_and_dumb_view_purity():
    """Verifica estructura core/shared/features y que ninguna vista dumb haga fetch o WebSocket."""
    js_root = ROOT_DIR / "src" / "presentation" / "web" / "static" / "js"
    for required in (
        js_root / "core" / "utils.js",
        js_root / "core" / "reactive_store.js",
        js_root / "core" / "api_client.js",
        js_root / "core" / "router.js",
        js_root / "shared" / "icons.js",
        js_root / "shared" / "skeleton_loader.js",
        js_root / "shared" / "toast.js",
        js_root / "shared" / "modal.js",
        js_root / "shared" / "empty_error_state.js",
    ):
        assert required.is_file(), f"Falta módulo requerido: {required}"

    feature_dirs = (
        "landing",
        "auth",
        "analytics_home",
        "tickets",
        "chat",
        "knowledge_base",
        "ai_agent",
        "ml_laboratory",
    )
    for feat in feature_dirs:
        view_file = js_root / "features" / feat / f"{feat}_view.js"
        container_file = js_root / "features" / feat / f"{feat}_container.js"
        assert view_file.is_file(), f"Falta vista dumb {view_file}"
        assert container_file.is_file(), f"Falta contenedor smart {container_file}"

        view_txt = view_file.read_text(encoding="utf-8")
        assert "fetch(" not in view_txt, f"Vista dumb {view_file} realiza fetch() directo"
        assert "new WebSocket" not in view_txt, f"Vista dumb {view_file} abre WebSocket directo"
        assert "CasagbiApi" not in view_txt, f"Vista dumb {view_file} acoplada a CasagbiApi"

        cont_txt = container_file.read_text(encoding="utf-8")
        assert "mount(" in cont_txt and "destroy(" in cont_txt


def test_js_helpers_router_guards_and_mount_destroy_lifecycle_via_node():
    """Ejecuta en Node.js pruebas reales de debounce 350ms, fechas Bogota, guardas RBAC y cero fugas mount/destroy."""
    utils_path = (ROOT_DIR / "src/presentation/web/static/js/core/utils.js").as_posix()
    router_path = (ROOT_DIR / "src/presentation/web/static/js/core/router.js").as_posix()
    store_path = (ROOT_DIR / "src/presentation/web/static/js/core/reactive_store.js").as_posix()

    node_script = f"""
const assert = require('assert');
const utils = require('{utils_path}');
const router = require('{router_path}');
const store = require('{store_path}');

// 1. Fechas en zona horaria America/Bogota (UTC-5)
const formatted = utils.formatBogotaDate('2026-11-17T05:30:00Z'); // 00:30 en Bogota
assert(formatted.includes('00:30'), 'Se esperaba hora 00:30 en America/Bogota, fue: ' + formatted);

// 2. Guardas RBAC y tab inicial home=kpis
assert.deepStrictEqual(router.getAllowedTabs('usuario'), ['kpis', 'tickets', 'create-ticket', 'kb']);
assert.strictEqual(router.resolveInitialTab('usuario', ''), 'kpis');
assert.strictEqual(router.resolveInitialTab('usuario', '#audit'), 'kpis'); // Bloqueado por guarda RBAC
assert.strictEqual(router.resolveInitialTab('admin', '#audit'), 'audit');
assert.strictEqual(router.isTabAllowed('director', 'create-ticket'), false);

// 3. ReactiveStore cache TTL y suscripciones limpias
store.setCache('k1', {{ ok: true }}, 5000, 1000);
assert.deepStrictEqual(store.getCache('k1', 2000), {{ ok: true }});
assert.strictEqual(store.getCache('k1', 7000), null);
const unsub = store.subscribe(() => {{}});
assert.strictEqual(store.getListenerCount(), 1);
unsub();
assert.strictEqual(store.getListenerCount(), 0);

// 4. Ciclo de vida mount()/destroy(): al navegar entre vistas no quedan timers ni AbortControllers activos
(async () => {{
  let activeTimers = 0;
  let activeAborts = 0;
  function makeDummyContainer() {{
    let tid = null;
    let ctrl = null;
    return {{
      async mount() {{
        ctrl = new AbortController();
        activeAborts += 1;
        tid = setTimeout(() => {{}}, 5000);
        activeTimers += 1;
      }},
      destroy() {{
        if (tid !== null) {{
          clearTimeout(tid);
          tid = null;
          activeTimers -= 1;
        }}
        if (ctrl !== null) {{
          ctrl.abort();
          ctrl = null;
          activeAborts -= 1;
        }}
      }},
    }};
  }}

  const lm = router.createLifecycleManager();
  lm.registerContainer('kpis', makeDummyContainer());
  lm.registerContainer('tickets', makeDummyContainer());
  lm.registerContainer('kb', makeDummyContainer());

  await lm.mountTab('kpis', 'admin');
  await lm.mountTab('tickets', 'admin');
  await lm.mountTab('kb', 'admin');
  const forbiddenRes = await lm.mountTab('audit', 'usuario');
  assert.strictEqual(forbiddenRes.mounted, false);
  lm.destroyActiveContainer();

  const stats = lm.getLifecycleStats();
  assert.strictEqual(stats.mountedCount, 3);
  assert.strictEqual(stats.destroyedCount, 3);
  assert.strictEqual(activeTimers, 0);
  assert.strictEqual(activeAborts, 0);

  // 5. Debounce 350ms y cancelación
  let calls = 0;
  const d = utils.debounce((v) => {{ calls += v; }}, 40);
  d(1);
  d(2);
  d(3);
  assert.strictEqual(calls, 0);
  await new Promise((r) => setTimeout(r, 70));
  assert.strictEqual(calls, 3);

  const dCancel = utils.debounce(() => {{ calls += 100; }}, 40);
  dCancel();
  dCancel.cancel();
  await new Promise((r) => setTimeout(r, 70));
  assert.strictEqual(calls, 3);

  console.log(JSON.stringify({{ ok: true, bogota: formatted }}));
}})();
"""
    proc = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True


def test_kpi_scope_and_riu10_csv_pdf_export(sprint3_client):
    """Exportación CSV y PDF RIU-10 respeta alcance del rol (RF-22) y devuelve cabeceras válidas."""
    client = sprint3_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    admin_headers = _auth_header(client, "admin@unicesar.edu.co")

    k_student = client.get("/api/v1/analytics/kpis", headers=student_headers).json()
    k_admin = client.get("/api/v1/analytics/kpis", headers=admin_headers).json()
    assert k_admin["kpis"]["total_tickets"] >= k_student["kpis"]["total_tickets"]
    assert "Mis solicitudes" in k_student["scope_label"]
    assert "institucional" in k_admin["scope_label"]

    csv_res = client.get("/api/v1/analytics/export.csv", headers=student_headers)
    assert csv_res.status_code == 200
    assert csv_res.headers["content-type"].startswith("text/csv")
    assert "informe_casagbi_riu10.csv" in csv_res.headers["content-disposition"]
    assert "RIU-10" in csv_res.text

    pdf_res = client.get("/api/v1/analytics/export.pdf", headers=admin_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.headers["x-content-type-options"] == "nosniff"
    assert pdf_res.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_res.content[-32:]


def test_landing_login_dashboard_accessibility_and_sections(sprint3_client):
    """Comprueba las 9 secciones de landing, tablas accesibles, Skip link, aria-live y guía de diseño."""
    client = sprint3_client
    assert (ROOT_DIR / "docs" / "guia-de-diseno.md").is_file()

    landing_html = client.get("/").text
    for expected_id in (
        'href="#main-content"',
        'id="servicios"',
        'id="como-funciona"',
        'id="consultar-radicado"',
        'id="asistente-ia"',
        'id="kb-publica"',
        'id="faq"',
        'id="sedes-contacto"',
        'id="privacidad"',
        "Ley 1581",
        "CONFIRMAR",
        "public-lookup-email",
    ):
        assert expected_id in landing_html

    login_html = client.get("/login").text
    assert 'id="login-status-banner"' in login_html
    assert "@unicesar.edu.co" in login_html

    dash_html = client.get("/dashboard").text
    for expected_dash in (
        'id="mobile-menu-btn"',
        'id="toggle-sidebar-btn"',
        'id="kpi-export-csv-btn"',
        'id="kpi-export-pdf-btn"',
        'id="table-by-service-body"',
        'id="table-tech-workload-body"',
        'id="tickets-search-indicator"',
        'id="kb-search-indicator"',
        'aria-live="polite"',
        "#0D1522",
        'id="resumen-greeting"',
        'id="resumen-status-banner"',
        'id="resumen-priority-bars"',
        'id="resumen-recent-tickets-tbody"',
        'id="resumen-sla-alert-btn"',
        'id="tickets-more-filters-btn"',
        'id="ct-or03-live-card"',
        'id="ct-open-ai-helper-btn"',
        'id="kb-reset-filters-btn"',
        'id="kb-contact-support-btn"',
        'id="view-teams"',
        'id="audit-restricted-notice"',
        'id="sidebar-help-btn"',
        "Asistente CASAGBI",
    ):
        assert expected_dash in dash_html


def test_resumen_analytics_payload_and_rbac_ui_refactors(sprint3_client):
    """Verifica datos reales de service_breakdown, open_by_priority, recent_attention_tickets y RBAC en router/icons JS."""
    client = sprint3_client
    coord_headers = _auth_header(client, "coordinador@unicesar.edu.co")
    tech_headers = _auth_header(client, "tecnico1@unicesar.edu.co")

    k_coord = client.get("/api/v1/analytics/kpis", headers=coord_headers).json()
    assert "csat_count" in k_coord["kpis"]
    assert "open_by_priority" in k_coord
    assert set(k_coord["open_by_priority"].keys()) == {"P1 Crítica", "P2 Alta", "P3 Media", "P4 Baja"}
    assert isinstance(k_coord["service_breakdown"], list)
    assert isinstance(k_coord["recent_attention_tickets"], list)
    if k_coord["recent_attention_tickets"]:
        sample = k_coord["recent_attention_tickets"][0]
        for key in ("id", "ticket_number", "title", "service_name", "priority", "status", "sla_status"):
            assert key in sample

    # Técnico tiene alcance de KPI propio (RF-22) y /audit-logs continúa bloqueado en servidor (403)
    k_tech = client.get("/api/v1/analytics/kpis", headers=tech_headers)
    assert k_tech.status_code == 200
    audit_denied = client.get("/api/v1/analytics/audit-logs", headers=tech_headers)
    assert audit_denied.status_code == 403

    icons_path = (ROOT_DIR / "src/presentation/web/static/js/shared/icons.js").as_posix()
    router_path = (ROOT_DIR / "src/presentation/web/static/js/core/router.js").as_posix()
    node_script = f"""
const assert = require('assert');
const icons = require('{icons_path}');
const router = require('{router_path}');

for (const name of ['grid', 'tickets', 'create', 'kb', 'users', 'activity', 'lifebuoy', 'wifi', 'clock', 'shieldCheck', 'chatBubble', 'sliders']) {{
  const markup = icons.svg(name);
  assert(markup.startsWith('<svg') && markup.includes('aria-hidden="true"'), 'Icono SVG invalido: ' + name);
}}

assert(router.getAllowedTabs('tecnico').includes('teams'));
assert(router.getAllowedTabs('tecnico').includes('audit'));
assert.strictEqual(router.isTabAllowed('usuario', 'audit'), false);
assert.strictEqual(router.isTabAllowed('director', 'create-ticket'), false);
console.log(JSON.stringify({{ ok: true }}));
"""
    proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    assert json.loads(proc.stdout.strip())["ok"] is True

