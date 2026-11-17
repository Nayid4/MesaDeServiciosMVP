# Evaluación Empírica del Clasificador NLP y Agente IA CASAGBI — Sprint 5

Esta evaluación mide de forma reproducible el comportamiento del clasificador NLP (`LinearSVC Calibrado` seleccionado como activo con latencia `0.2283 ms`, sobre TF-IDF 1–2 con sinónimos TIC, *stopwords* en español y umbral mínimo de confianza `0,60`) y del agente conversacional **CASAGBI Agent** sobre un conjunto de **105 frases** (`EVALUATION_DATASET_105` en `src/infrastructure/ml/agent_evaluator.py`).

---

## 1. Corrección de la Causa Raíz del Sprint 0

En el Sprint 0 (`docs/00-diagnostico.md`) la frase `"tengo un problema con una computadora que no prende"` era clasificada erróneamente como *Aulas Inteligentes y Videoproyectores (88,9 %)* por OOV de `computadora`/`prende`, ausencia de *stopwords* y sesgo del bigrama `"que no"`, y el agente asumía silenciosamente `Sede Sabanas (Valledupar)`, `Bloque A` y `P3 Media`.

**Resultado verificado tras las correcciones del Sprint 5:**
- **Entrada:** `"tengo un problema con una computadora que no prende"`
- **Servicio predicho:** `Equipos de Cómputo e Impresoras` (**`97,68 %`** de confianza, $\ge 60\%$)
- **Sede asumida:** `null` (ninguna)
- **Ubicación asumida:** `null` (ninguna)
- **Urgencia asumida:** `null` (ninguna)
- **Estado del agente (`agent_status`):** `needs_missing_fields` — pregunta explícitamente **`["sede", "location", "urgency"]`** antes de construir el borrador editable.

---

## 2. Métricas del Pipeline ML Reentrenado (`18.000` registros CRISP-DM)

- **Limpieza CRISP-DM:** `18.000` crudos $\rightarrow$ `17.658` limpios (`98,1 %` retención; `342` excluidos; ganancia del modelo activo frente al baseline: `+8,61 %` F1 Macro).

| Modelo | CV 5-Fold F1 | F1-Score Macro (Test 80/20) | Accuracy | Latencia (ms/ticket) |
|---|---|---|---|---:|
| `keyword_baseline` (Reglas + sinónimos TIC) | `0.8829` | `0.8847` | `0.8785` | `0.2431` |
| `multinomial_nb` (`Alpha=0.5`) | `0.9736` | `0.9708` | `0.9731` | `0.2439` |
| `logistic_regression` (`C=2.0`) | `0.9736` | `0.9708` | `0.9731` | `0.2426` |
| `linear_svc` (Calibrado, **Activo**) | `0.9736` | `0.9708` | `0.9731` | `0.2283` |

---

## 3. Resultados del Conjunto de Evaluación (`105` frases)

| Subconjunto | Frases | Aciertos correctos | Tasa de acierto |
|---|---:|---:|---:|
| Uso real en dominio (con sinónimos coloquiales) | `55` | `54` | `98,18 %` |
| Errores de escritura (*typos*) | `20` | `20` | `100,00 %` |
| **Total en dominio (uso real + *typos*)** | **`75`** | **`74`** | **`98,67 %`** |
| Frases ambiguas (`confidence < 0,60` $\rightarrow$ `needs_clarification`) | `15` | `15` | `100,00 %` |
| Frases fuera de alcance (`RNF-13` $\rightarrow$ `out_of_scope`) | `15` | `15` | `100,00 %` |
| **Total tasa «no sé» / fuera de alcance correcta** | **`30`** | **`30`** | **`100,00 %`** |
| **Total global evaluado** | **`105`** | **`104`** | **`99,05 %`** |

**Único caso límite observado (`1 / 105`):**
- `"olvidé la contraseña para entrar al vortal académico"`: clase predicha correcta (`Plataformas Académicas (Aula Web / Vortal)`), pero la calibración multi-señal repartió probabilidad con `Correo Institucional y Cuentas` (confianza `56,42 % < 60 %`) y solicitó aclaración manual (`needs_clarification` si `confidence < 0,60`). Tras incorporar `"no hay internet"`, `"switch"` e `"internet"` en `_SYNONYM_PATTERNS`, la frase de conectividad `"no hay internet en ningún computador del bloque b"` pasó a clasificarse correctamente.
