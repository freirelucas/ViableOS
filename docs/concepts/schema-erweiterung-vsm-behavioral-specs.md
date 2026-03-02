# Schema-Erweiterung: VSM Behavioral Specifications

## Problem

Das aktuelle Schema (`ViableSystem`) beschreibt **Topologie** (welche Units, welche Checks, welche Quellen) — aber nicht **Verhalten** (wann eskaliert wer, wie schließt sich ein Regelkreis, was ändert sich in einer Krise).

Die Generatoren (`generator.py`, `soul_templates.py`) kompensieren das durch hardcodierte Texte in SOUL.md und SKILL.md. Ergebnis: Alle Organisationen bekommen dasselbe Verhalten, unabhängig von ihrem Kontext.

## Design-Prinzip

**Config beschreibt WAS, Generatoren entscheiden WIE.**

Aber: Das WAS muss reichhaltiger werden. Der Assessment-Dialog kennt die Organisation gut genug, um domänenspezifisches Verhalten abzuleiten. Beispiel: Ein Pflegedienst braucht andere Eskalations-Schwellen als ein Software-Startup.

## Strategie: Drei Schichten

```
Schicht 1: Config-Schema (TypeScript + Python)
    ↓ Was die Organisation braucht
Schicht 2: Assessment-Transformer
    ↓ Leitet Verhalten aus Kontext ab
Schicht 3: Generatoren (SOUL.md, SKILL.md, HEARTBEAT.md)
    ↓ Übersetzt in Agent-lesbare Markdown-Instruktionen
```

Alle neuen Felder sind **optional** mit sinnvollen Defaults. Bestehende Configs bleiben 100% kompatibel.

---

## Neue Schema-Felder

### 1. System-weit: `operational_modes`

Drei Modi die ALLE Agenten betreffen. Jede Organisation definiert ihre eigenen Schwellen.

```typescript
// In ViableSystem (top-level)
operational_modes?: {
  normal: {
    description: string;           // "Tagesbetrieb, volle Autonomie der Einheiten"
    s1_autonomy: 'full' | 'standard' | 'restricted';
    reporting_frequency: string;   // "weekly"
    escalation_threshold: string;  // "2 Stunden ohne Reaktion"
  };
  elevated: {
    description: string;           // "Erhöhte Wachsamkeit bei externem Druck"
    triggers: string[];            // ["Kundenbeschwerde-Rate > 5%", "Mitarbeiter-Ausfall > 20%"]
    s1_autonomy: 'full' | 'standard' | 'restricted';
    reporting_frequency: string;   // "daily"
    escalation_threshold: string;  // "30 Minuten ohne Reaktion"
  };
  crisis: {
    description: string;           // "Akute Krise, zentrale Steuerung"
    triggers: string[];            // ["Datenverlust", "Regulatorische Anordnung", "Umsatzeinbruch > 30%"]
    s1_autonomy: 'full' | 'standard' | 'restricted';
    reporting_frequency: string;   // "hourly"
    escalation_threshold: string;  // "sofort"
    human_required: boolean;       // true — Mensch muss den Krisenmodus aktivieren
  };
};
```

**Warum:** Aktuell reagieren alle Agenten immer gleich. Ein Pflegedienst bei Personalausfall braucht sofortige Umschaltung auf Krisenmodus — ein Software-Team braucht das erst bei Datenverlust.

**Generator-Impact:** SKILL.md bekommt einen "Operational Modes" Abschnitt. HEARTBEAT.md passt Frequenzen an den aktiven Modus an.

### 2. System-weit: `escalation_chains`

Wer eskaliert an wen, wann, mit welcher Dringlichkeit.

```typescript
// In ViableSystem (top-level)
escalation_chains?: {
  operational: {
    // S1 → S2 → S3 → Mensch
    path: string[];               // ["s2-coordination", "s3-optimization", "human"]
    timeout_per_step: string;     // "2h" — wenn keine Reaktion, nächste Stufe
  };
  quality: {
    // S3* → S3 → Mensch
    path: string[];
    timeout_per_step: string;
  };
  strategic: {
    // S4 → S5 → Mensch
    path: string[];
    timeout_per_step: string;
  };
  algedonic: {
    // Jeder → S5 → Mensch (Bypass aller Ebenen)
    description: string;          // "Schmerzsignal bei fundamentalem Problem"
    triggers: string[];           // ["Werteverstoß", "Illegale Anweisung", "Gefährdung von Personen"]
    path: string[];               // ["s5-policy", "human"]
  };
};
```

**Warum:** Aktuell steht "escalate to Coordinator" in SKILL.md, aber es fehlt: Timeout, Dringlichkeit, was passiert wenn S2 nicht reagiert, und der algedonische Bypass.

**Generator-Impact:** Jeder Agent bekommt einen "Escalation Protocol" Abschnitt in SKILL.md mit seiner konkreten Kette.

### 3. System-weit: `vollzug_protocol`

Der Vier-Schritt-Regelkreis nach Pfiffner.

```typescript
// In ViableSystem (top-level)
vollzug_protocol?: {
  enabled: boolean;               // true
  steps: ['auftrag', 'quittung', 'vollzug', 'bestätigung'];
  timeout_quittung: string;       // "30min" — wie lange auf Auftragsquittung warten
  timeout_vollzug: string;        // "24h" — wie lange auf Vollzugsmeldung warten
  on_timeout: 'escalate' | 'remind' | 'alert_human';
};
```

**Warum:** Pfiffner: "Nur wenn wir die Antwort gehört haben, wissen wir was wir gesagt haben." Aktuell gibt es keine Pflicht, Aufträge zu quittieren oder Ergebnisse zu melden. Aufgaben verschwinden im Nichts.

**Generator-Impact:** Jeder S1-Agent bekommt in SKILL.md die Pflicht: "Auf jeden Auftrag antwortest du mit einer Quittung. Nach Erledigung sendest du eine Vollzugsmeldung." S3-Agent bekommt: "Offene Aufträge ohne Quittung nach {timeout} eskalieren."

### 4. S1-Unit-Erweiterung: `autonomy_levels`

Strukturiert statt Freitext.

```typescript
// In S1Unit
autonomy_levels?: {
  can_do_alone: string[];         // ["Kundenanfragen beantworten", "Routine-Reports erstellen"]
  needs_coordination: string[];   // ["Preisänderungen", "Terminverschiebungen mit anderen Units"]
  needs_approval: string[];       // ["Vertragsänderungen", "Budget > 500€", "Neue Mitarbeiter-Zugänge"]
};
```

**Warum:** `autonomy: string` ist zu unstrukturiert. Der Generator kann daraus keine klaren Entscheidungsbäume bauen. Strukturiert → Agent weiß genau: "Das darf ich allein, das muss ich abstimmen, das braucht den Chef."

**Generator-Impact:** SOUL.md § "What you can do alone" wird zu drei klaren Listen. SKILL.md bekommt eine Entscheidungsmatrix.

### 5. S2-Erweiterung: `conflict_detection` + `transduction`

```typescript
// In system_2
system_2?: {
  coordination_rules?: CoordinationRule[];
  conflict_detection?: {
    resource_overlaps: boolean;      // true — automatisch Ressourcen-Kollisionen erkennen
    deadline_conflicts: boolean;     // true — Terminüberschneidungen erkennen
    output_contradictions: boolean;  // true — widersprüchliche Outputs erkennen
    custom_triggers?: string[];      // ["Wenn beide Teams den selben Kunden kontaktieren wollen"]
  };
  transduction_mappings?: Array<{
    from_unit: string;              // "Abrechnung"
    to_unit: string;                // "Planung"
    translation: string;            // "Was Abrechnung 'Leistungsnachweis' nennt, ist für Planung der 'Wochenplan-Output'"
  }>;
  escalation_to_s3_after?: string;  // "2 gescheiterte Mediationsversuche"
};
```

**Warum:** S2 ist aktuell ein passiver Router. Mit Conflict Detection wird er zum aktiven Frühwarnsystem. Transduction löst das Problem, dass S1-Einheiten verschiedene Fachsprachen sprechen.

**Generator-Impact:** SOUL.md § "Behavior" wird konkret: "Prüfe bei jeder Aktion von Unit A ob sie mit Unit B kollidiert." SKILL.md bekommt ein Glossar der Fachsprachen-Übersetzungen.

### 6. S3-Erweiterung: `triple_index` + `deviation_logic` + `intervention_authority`

```typescript
// In system_3
system_3?: {
  reporting_rhythm?: string;
  resource_allocation?: string;
  kpi_list?: string[];
  triple_index?: {
    actuality: string;              // "Was leistet die Einheit gerade tatsächlich?"
    capability: string;             // "Was könnte sie leisten bei optimaler Auslastung?"
    potentiality: string;           // "Was könnte sie leisten wenn wir investieren?"
    measurement: string;            // "Stunden, Umsatz, Output-Menge" — domänenspezifisch
  };
  deviation_logic?: {
    report_only_deviations: boolean; // true — nicht "alles ist normal" melden
    threshold_percent?: number;      // 15 — Abweichung > 15% = melden
    trend_detection: boolean;        // true — 3x hintereinander leichter Rückgang = melden
  };
  intervention_authority?: {
    can_restrict_s1_autonomy: boolean;   // true
    requires_documentation: boolean;     // true — jede Intervention muss begründet werden
    requires_human_approval: boolean;    // false — in Krise darf S3 sofort handeln
    max_duration: string;                // "48h" — danach muss Mensch bestätigen
    allowed_actions: string[];           // ["Budget einfrieren", "Aufgabe umleiten", "Modell downgraden"]
  };
};
```

**Warum:**
- **Triple Index** (Beer): Actuality/Capability/Potentiality ist DAS Steuerungsinstrument. Aktuell fehlt es komplett.
- **Deviation Logic**: "Alles ist normal" ist kein Report. Nur Abweichungen melden spart Token-Budget und Aufmerksamkeit.
- **Intervention Authority**: Kanal 3 (Corporate Intervention) ist der einzige Kanal auf dem S3 die Autonomie von S1 einschränken darf. Muss explizit definiert und protokolliert werden.

**Generator-Impact:** SOUL.md bekommt Triple-Index als Steuerungsrahmen. SKILL.md bekommt Deviation-Logik und Interventionsprotokoll.

### 7. S3*-Erweiterung: `provider_constraint` + `audit_methodology`

```typescript
// In system_3_star
system_3_star?: {
  checks?: Array<{
    name: string;
    target: string;
    method: string;
    // NEU:
    data_source?: 'raw_data' | 'agent_output' | 'both';  // Was wird geprüft
    comparison?: string;            // "Vergleiche gemeldete Stunden mit tatsächlichen Zeitstempeln"
  }>;
  on_failure?: string;
  provider_constraint?: {
    must_differ_from: 's1' | 'all';  // Provider muss sich von S1 (oder allen) unterscheiden
    reason: string;                   // "Verhindert korrelierte Halluzinationen"
  };
  reporting_target?: 's3' | 's3_and_human';  // An wen — NIE direkt an S1
  independence_rules?: string[];     // ["Kein Schreibzugriff auf S1-Workspaces", "Kein Zugang zu S1-Prompts"]
};
```

**Warum:** Provider-Constraint steht im Checker als Warning, muss aber ins Schema als harte Architektur-Entscheidung. Audit-Methodology braucht pro Check eine Definition was gegen was verglichen wird.

**Generator-Impact:** SOUL.md § "Independence" wird mit konkreten Regeln gefüllt. SKILL.md § "Verification Methodology" bekommt pro Check die Vergleichslogik.

### 8. S4-Erweiterung: `premises_register` + `strategy_bridge`

```typescript
// In system_4
system_4?: {
  monitoring?: { ... };  // wie bisher
  premises_register?: Array<{
    premise: string;                // "Fachkräfte sind am Markt verfügbar"
    check_frequency: string;        // "monthly"
    invalidation_signal: string;    // "Bewerbungseingang sinkt 3 Monate in Folge"
    consequence_if_invalid: string; // "Strategie 'Wachstum durch Neueinstellung' funktioniert nicht mehr"
  }>;
  strategy_bridge?: {
    injection_point: string;        // "Vor der operativen Quartalsplanung"
    format: string;                 // "Strategisches Briefing mit max. 3 Handlungsempfehlungen"
    recipient: string;              // "s3-optimization"
  };
  weak_signals?: {
    enabled: boolean;
    unconventional_sources?: string[];  // ["Branchenfremde Innovationen", "Kundenbeschwerden-Muster"]
    detection_method: string;           // "Mustererkennung über 3-Monats-Fenster"
  };
};
```

**Warum:**
- **Premises Register**: Pfiffner-Beispiel: Konzern plant Budget (September) vor Strategie (November). Ergebnis: Strategie wird nie operativ. Ein Register zwingt zur Prüfung: "Stimmen unsere Annahmen noch?"
- **Strategy Bridge**: S4-Erkenntnisse müssen zeitgerecht in die operative Planung einfließen — nicht "irgendwann per Email".

**Generator-Impact:** SOUL.md bekommt "Premises to watch" Liste. HEARTBEAT.md bekommt Prämissen-Check im passenden Rhythmus. SKILL.md bekommt das Format für die Strategy-Bridge.

### 9. S5-Erweiterung: `balance_monitoring` + `algedonic_channel` + `basta_constraint`

```typescript
// In Identity (erweitert)
identity?: {
  purpose: string;
  values?: string[];
  never_do?: string[];
  decisions_requiring_human?: string[];
  // NEU:
  balance_monitoring?: {
    s3_vs_s4_target: string;        // "60/40" — 60% operative Optimierung, 40% Zukunft
    measurement: string;            // "Anteil der Agent-Tokens die in S3 vs S4 fließen"
    alert_if_exceeds: string;       // "80/20" — Alarm wenn Optimierung S4 verdrängt
  };
  algedonic_channel?: {
    enabled: boolean;
    who_can_send: 'all_agents' | 's1_only' | 'all_agents_and_human';
    triggers: string[];             // ["Werteverstoß erkannt", "Illegale Anweisung erhalten", "Systemische Fehlfunktion"]
    bypasses_hierarchy: boolean;    // true — geht direkt an S5, überspringt S2/S3
  };
  basta_constraint?: {
    description: string;            // "Normative Entscheide bei Unentscheidbarkeit"
    examples: string[];             // ["Strategiewechsel", "Fusion/Übernahme", "Ethik-Dilemma"]
    agent_role: 'prepare_only';     // Agent bereitet vor, entscheidet NICHT
  };
};
```

**Warum:**
- **Balance Monitoring**: Die häufigste VSM-Pathologie ist dass S3 (Tagesgeschäft) S4 (Zukunft) komplett verdrängt. Muss gemessen werden.
- **Algedonic Channel**: Einziger Kanal der alle Ebenen durchstößt. Fehlt komplett.
- **Basta Constraint**: Explizit machen was der Agent NICHT kann. Verhindert dass der Agent sich anmaßt, normative Entscheide zu treffen.

**Generator-Impact:** SOUL.md § "S3/S4 Balance" und "Algedonic Signal" als neue Abschnitte. HEARTBEAT.md: Balance-Messung im Wochenrhythmus.

---

## Assessment-Transformer: Was automatisch abgeleitet wird

Der Assessment-Dialog kennt die Organisation. Daraus kann der Transformer vieles ableiten, ohne dass der User jedes Feld einzeln ausfüllen muss:

| Schema-Feld | Abgeleitet aus |
|-------------|---------------|
| `operational_modes.elevated.triggers` | `external_forces` (Risiken) + `team.size` (kleine Teams = schneller in Krise) |
| `operational_modes.crisis.triggers` | `success_criteria` mit priority 1 (Inversion: Wenn das scheitert = Krise) |
| `escalation_chains.operational.timeout` | `team.size` (1-2 Pers. = kurze Timeouts, 10+ = längere) |
| `escalation_chains.algedonic.triggers` | `identity.never_do` (Verstoß = algedonisches Signal) |
| `vollzug_protocol.timeout_quittung` | `operational_modes.normal.reporting_frequency` (proportional) |
| `s1.autonomy_levels.needs_approval` | `human_in_the_loop.approval_required` (pro Unit aufschlüsseln) |
| `s2.conflict_detection.custom_triggers` | `dependencies` (jede Dependency = potentieller Konflikt) |
| `s2.transduction_mappings` | `dependencies` + `s1.domain_context` (Fachsprachen-Unterschiede) |
| `s3.triple_index.measurement` | `success_criteria` + `s3.kpi_list` (was gemessen wird) |
| `s3.deviation_logic.threshold` | `budget.strategy` ("frugal" = 10%, "balanced" = 15%, "generous" = 20%) |
| `s3.intervention_authority.allowed_actions` | `human_in_the_loop.approval_required` (Inverse: was NICHT allein geht) |
| `s3_star.provider_constraint` | Immer `must_differ_from: 's1'` (kein Assessment nötig) |
| `s4.premises_register` | `external_forces` → jede Force wird zu einer Prämisse |
| `s4.strategy_bridge.injection_point` | `s3.reporting_rhythm` (immer VOR dem Reporting-Zyklus) |
| `identity.balance_monitoring.s3_vs_s4_target` | `budget.strategy` ("frugal" = 70/30, "balanced" = 60/40, "generous" = 50/50) |
| `identity.algedonic_channel.triggers` | `identity.never_do` + "Systemische Fehlfunktion" |

**Prinzip:** Der User muss nur das Assessment-Interview durchlaufen. Der Transformer leitet die Behavioral Specs automatisch ab. Im Wizard kann der User die Defaults überschreiben.

---

## Auswirkung auf die Generatoren

### SOUL.md — Neue Abschnitte

Für **jeden Agenten** kommen hinzu:

```markdown
## Operational Modes
- **Normal**: {description}. Du arbeitest selbstständig.
- **Erhöhte Aktivität**: Getriggert durch {triggers}. Reporting-Frequenz steigt auf {freq}.
- **Krise**: Getriggert durch {triggers}. Du wartest auf Anweisungen von S3.
  Autonomie: {level}. Jede Aktion braucht Vollzugsmeldung.

## Escalation Protocol
Deine Eskalationskette: {path}
Timeout pro Stufe: {timeout}
Bei algedonischem Signal (Werteverstoß, Gefährdung): Direkt an S5 → Mensch.
```

Für **S1** kommt hinzu:

```markdown
## Autonomy Matrix
### Allein entscheiden
{can_do_alone}
### Koordination nötig (über S2)
{needs_coordination}
### Genehmigung nötig (Mensch)
{needs_approval}

## Vollzug-Pflicht
Auf jeden Auftrag antwortest du mit einer Quittung innerhalb von {timeout_quittung}.
Nach Erledigung sendest du eine Vollzugsmeldung.
Ohne Vollzugsmeldung gilt der Auftrag als NICHT erledigt.
```

Für **S3** kommt hinzu:

```markdown
## Triple Index
Für jede Einheit misst du:
- **Actuality**: {actuality} — was leistet sie jetzt?
- **Capability**: {capability} — was könnte sie bei Vollauslastung?
- **Potentiality**: {potentiality} — was wäre mit Investition möglich?
Maßeinheit: {measurement}

## Abweichungs-Logik
Melde NUR Abweichungen > {threshold}%. "Alles normal" ist KEIN Report.
Bei 3x hintereinander leichtem Rückgang: Trend melden, auch wenn Einzelwert unter Schwelle.

## Interventionsrecht (Kanal 3)
Du DARFST in begründeten Fällen:
{allowed_actions}
ABER: Jede Intervention muss dokumentiert und begründet werden.
Maximale Dauer ohne Mensch-Bestätigung: {max_duration}.
```

Für **S4** kommt hinzu:

```markdown
## Prämissen-Register
Folgende Annahmen musst du kontinuierlich prüfen:
{for each premise:}
- **{premise}** — Prüfen: {check_frequency}
  Invalidierungs-Signal: {invalidation_signal}
  Wenn ungültig: {consequence_if_invalid}

## Strategy Bridge
Deine Erkenntnisse fließen ein: {injection_point}
Format: {format}
Empfänger: {recipient}
```

Für **S5** kommt hinzu:

```markdown
## S3/S4 Balance
Ziel-Verhältnis: {s3_vs_s4_target}
Messung: {measurement}
Alarm wenn: {alert_if_exceeds}

## Algedonischer Kanal
Jeder Agent kann bei {triggers} ein Signal direkt an dich senden.
Dieses Signal umgeht die Hierarchie. Du leitest es SOFORT an den Menschen weiter.

## Basta-Vorbehalt
Folgende Entscheide triffst du NIEMALS selbst: {examples}
Deine Rolle: Entscheidungsvorlage vorbereiten (Kontext, Optionen, Empfehlung, Dringlichkeit).
Der Mensch entscheidet. Du setzt um.
```

### HEARTBEAT.md — Modusabhängige Frequenzen

```markdown
## Frequenzen nach Betriebsmodus

| Check | Normal | Erhöht | Krise |
|-------|--------|--------|-------|
| Status-Report | weekly | daily | hourly |
| Vollzugs-Check | daily | every 4h | hourly |
| Prämissen-Check (S4) | monthly | weekly | daily |
| Balance-Check (S5) | weekly | daily | daily |
| Audit-Sample (S3*) | every 4h | every 2h | every 1h |
```

### SKILL.md — Neue Abschnitte

Für **S2** kommt hinzu:

```markdown
## Conflict Detection
Automatisch prüfen:
{if resource_overlaps} - Ressourcen-Überlappung zwischen Einheiten
{if deadline_conflicts} - Terminkonflikt erkennen
{if output_contradictions} - Widersprüchliche Outputs erkennen
{custom_triggers}

## Fachsprachen-Übersetzung (Transduktion)
{for each mapping:}
- {from_unit} sagt "{x}" → {to_unit} versteht das als "{y}"
```

---

## Wizard-Erweiterung

Die neuen Felder brauchen KEINE neuen Wizard-Steps. Sie werden:

1. **Automatisch abgeleitet** vom Assessment-Transformer (80%)
2. **Auf dem ReviewStep (Step 6) angezeigt** als Abschnitt "Behavioral Specs" mit Aufklapp-Details
3. **Editierbar** über einen optionalen "Advanced" Bereich im Wizard

Der ReviewStep bekommt einen neuen Abschnitt:

```
📋 Behavioral Specifications (auto-generated)
├── Operational Modes: Normal / Erhöht (2 Trigger) / Krise (3 Trigger)
├── Escalation: S1→S2→S3→Mensch (2h timeout)
├── Vollzug-Protokoll: aktiv (30min Quittung, 24h Vollzug)
├── S3 Intervention: erlaubt (Budget einfrieren, Aufgabe umleiten)
├── S3* Provider: muss abweichen von S1
├── S4 Prämissen: 4 überwachte Annahmen
├── S3/S4 Balance: Ziel 60/40, Alarm bei 80/20
└── Algedonischer Kanal: aktiv (3 Trigger)
```

---

## Änderungs-Übersicht

### Dateien die geändert werden

| Datei | Änderung | Aufwand |
|-------|----------|---------|
| `frontend/src/types/index.ts` | Neue Interfaces + erweiterte bestehende | mittel |
| `src/viableos/assessment_transformer.py` | Neue Builder-Funktionen für jedes Feld | groß |
| `src/viableos/soul_templates.py` | Neue Abschnitte in jeder `generate_*_soul()` | groß |
| `src/viableos/generator.py` | Neue Felder an Soul/Skill/Heartbeat-Generatoren durchreichen | mittel |
| `src/viableos/checker.py` | Neue Checks (Modes definiert? Vollzug aktiv? etc.) | klein |
| `src/viableos/coordination.py` | Conflict Detection + Transduction integrieren | klein |
| `frontend/src/components/wizard/ReviewStep.tsx` | "Behavioral Specs" Abschnitt | klein |

### Dateien die NICHT geändert werden

- `chat/` — Chat-Flow bleibt gleich
- `system_prompt.py` — Assessment-Interview bleibt gleich (die neuen Felder werden abgeleitet, nicht abgefragt)
- `budget.py` — Budget-Logik bleibt gleich
- `langgraph_generator.py` — Separat, kann später nachziehen

---

## Reihenfolge der Implementierung

### Phase 1: Schema + Transformer (Backend-only, kein UI nötig)
1. TypeScript-Types erweitern
2. Python-Dataclasses / Dicts erweitern
3. `assessment_transformer.py` — Ableitungslogik für jedes neue Feld
4. Tests: Bestehende Assessments transformieren → neue Felder werden befüllt

### Phase 2: Generatoren (Output wird besser)
5. `soul_templates.py` — Neue Abschnitte pro System
6. `generator.py` — Neue Felder durchreichen
7. Tests: Generierte SOUL.md / SKILL.md / HEARTBEAT.md prüfen

### Phase 3: Checker + UI (Validierung + Sichtbarkeit)
8. `checker.py` — Neue Viability-Checks
9. `ReviewStep.tsx` — Behavioral Specs anzeigen
10. Optional: Advanced-Edit im Wizard

---

## Beispiel: Komplettes Schema nach Erweiterung

```typescript
export interface ViableSystem {
  name: string;
  runtime?: string;
  identity: Identity;                    // erweitert um balance_monitoring, algedonic, basta
  system_1: S1Unit[];                    // erweitert um autonomy_levels
  system_2?: System2;                    // erweitert um conflict_detection, transduction
  system_3?: System3;                    // erweitert um triple_index, deviation_logic, intervention
  system_3_star?: System3Star;           // erweitert um provider_constraint, audit_methodology
  system_4?: System4;                    // erweitert um premises_register, strategy_bridge
  budget?: Budget;
  model_routing?: ModelRouting;
  human_in_the_loop?: HumanInTheLoop;
  persistence?: Persistence;
  // NEU:
  operational_modes?: OperationalModes;
  escalation_chains?: EscalationChains;
  vollzug_protocol?: VollzugProtocol;
}
```
