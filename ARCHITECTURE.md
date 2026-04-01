# VoiTomation — System Architecture

**Voice + Automation**: Secure, voice-driven AAA and infrastructure automation powered by AI agents.

---

## 1. Vision

Current PE/SRE tooling (Terraform, Ansible, Kerberos, Puppet) requires deep specialist expertise. The result is bottlenecks, syntax errors, steep onboarding curves, and dependency on a small number of experts.

VoiTomation reframes this with an **expert + apprentice model**:

- **One human expert** (e.g., Chris) holds authority — roles, permissions, approval rights.
- **One AI assistant** (e.g., Lily) holds knowledge — syntax, tool invocation, plan generation.
- **Together** they accomplish in seconds what previously required specialists.

The human says *what* they want. The AI knows *how* to do it. Security and auditability are built in, not bolted on.

---

## 2. Core Concepts

### 2.1 Personas

| Persona | Type | Role |
|---|---|---|
| **Chris** | Human operator/admin | Issues voice commands; holds permissions |
| **Lily** | AI agent (Claude-based) | Interprets intent; generates and executes plans; holds no independent permissions |

### 2.2 Dual Blockchain

| Ledger | Write access | Contents | Mutability |
|---|---|---|---|
| **Blockchain A** — Identity & Permissions | Enrollment authority only | Chris's roles, permissions, identity hashes | Immutable |
| **Blockchain B** — Audit Trail | System only (append-only) | Every command, plan, governance decision, execution step, outcome | Append-only |

Neither Chris nor Lily can write to Blockchain A at runtime. This means a compromised Lily cannot escalate her own permissions.

### 2.3 Pass-Through Authentication

Lily has **no independent cloud permissions**. She acts as an authenticated proxy for Chris:

1. Chris speaks → voice auth succeeds → short-lived scoped token minted (JWT).
2. Token encodes: Chris's identity, permission scope, session expiry, auth confidence score.
3. Lily presents this token to cloud APIs. Cloud sees *Chris's* authorization, not Lily's.
4. This maps to existing cloud patterns: GCP Workload Identity, AWS `sts:AssumeRole`, Azure Managed Identity.

The novel element: the token is derived from a **voice auth event**, not a static credential.

### 2.4 Tiered Governance

| Tier | Example Actions | Auth Requirement | Confirmation |
|---|---|---|---|
| **1 — Read** | `ls`, query status, read logs | Initial voice auth | None |
| **2 — Non-destructive Write** | Stage deployment, create non-prod resources | Continuous session auth | Implicit (Lily presents plan) |
| **3 — Risky/Costly** | Deploy to production, create expensive resources | Continuous auth | Explicit voice confirmation |
| **4 — Destructive/Irreversible** | Delete data, modify IAM, override safety | QRNG challenge phrase + re-confirm | Challenge response + time delay |

---

## 3. Five-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Voice Authentication                          │
│  Who issued this command?                               │
│  Voice biometrics → identity claim → session token      │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Continuous Session Auth                       │
│  Is this still Chris?                                   │
│  Behavioral monitoring throughout session               │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Intent + Governance Gate                      │
│  What does Chris want, and is it allowed?               │
│  Utterance → intent object → structured plan →          │
│  policy check → scope validation → SOP compliance       │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Bounded Execution                             │
│  Execute exactly what was authorized, nothing more      │
│  Sandboxed agent runtime → step monitoring → drift halt │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Audit & Verification                          │
│  Cryptographic chain of trust, voice to outcome         │
│  Blockchain B: command → plan → gate → exec → outcome   │
└─────────────────────────────────────────────────────────┘
```

---

## 4. System Data Flow

```
Chris speaks
     │
     ▼
[Voice Capture] ─── raw audio ──► [Voice Auth Service]
                                        │
                              identity claim + confidence
                                        │
                                        ▼
                              [Blockchain A lookup]
                              "Does Chris have permission
                               for this action class?"
                                        │
                                  YES / NO / TIER
                                        │
                                        ▼
                              [Intent Extraction (Lily)]
                              utterance → structured intent:
                              { action, target, scope, constraints }
                                        │
                                        ▼
                              [Plan Generation (Lily)]
                              intent → step-by-step execution plan
                                        │
                                        ▼
                              [Governance Gate]
                              ├── Policy enforcement (IAM)
                              ├── Scope constraint validator
                              ├── SOP compliance checker
                              └── Resource existence validator
                                        │
                              PASS / FAIL / MODIFY
                                        │
                                        ▼
                         [Tier check — confirmation required?]
                              │                    │
                           Tier 1-2             Tier 3-4
                           auto-proceed    voice confirmation
                                                   │
                                        [Bounded Execution]
                                        sandboxed runtime
                                        step-by-step monitoring
                                        drift detection
                                               │
                                               ▼
                                    [Audit Write → Blockchain B]
                                    hash-chained ledger entry:
                                    auth event → intent → plan →
                                    gate result → execution log →
                                    outcome state hash
```

---

## 5. Technology Stack

### 5.1 Core Stack (All Increments)

| Component | Technology | Rationale |
|---|---|---|
| **Lily agent** | Python + Anthropic SDK (`claude-opus-4-6`) | Best-in-class reasoning, tool use, adaptive thinking |
| **Voice capture** | `sounddevice` / `pyaudio` | Cross-platform mic access |
| **Speech-to-text** | Google Cloud Speech-to-Text | GCP-native, high accuracy |
| **Agent framework** | Anthropic tool use (manual loop) | Full control over governance gate injection |
| **Cloud target** | GCP | Terraform provider, IAM, Workload Identity |
| **Infrastructure tool** | Terraform via `subprocess` / GCP Python SDK | Primary automation surface |
| **Linux tool** | `subprocess` with allowlist | Bounded shell execution |

### 5.2 Per-Increment Stack

| Layer | Inc 1 | Inc 2 | Inc 3 |
|---|---|---|---|
| Voice auth | Stub (pass-through, no biometrics) | Classical speaker verification (SpeechBrain / Azure Speaker Recognition) | Quantum-enhanced (Qiskit PQC kernel + HDC) |
| Blockchain A | Static YAML/JSON permission store | Hyperledger Fabric (permissioned) | Hyperledger + ZK-proof layer |
| Blockchain B | Hash-chained append-only log (SQLite + SHA-256) | Hyperledger Fabric audit channel | Hyperledger + public chain attestation |
| Session auth | Single auth event | Continuous behavioral scoring | QC-enhanced + QRNG challenges |
| Agent count | Single (Lily) | Lily + specialist sub-agents | Multi-agent mesh |
| Deployment | Local / single machine | GCP Cloud Run + GKE | GCP + local/edge (K8s, air-gapped) |

---

## 6. Incremental Plan

### Increment 1 — Core Pipeline (Build Now)

**Goal**: Prove the accessibility story. Chris speaks → Lily acts → audit trail exists.

**Scope**:
- [ ] Lily agent: utterance → intent object → structured plan → tool execution
- [ ] Tool set: Linux (allowlisted shell), GCP Terraform, GCP resource query
- [ ] Permission store: static YAML (Blockchain A stub)
- [ ] Audit log: hash-chained SQLite ledger (Blockchain B stub)
- [ ] Governance gate: OPA/Rego rules for scope + SOP validation
- [ ] Tiered confirmation: Tier 1-2 auto, Tier 3-4 text confirmation (voice confirmation in Inc 2)
- [ ] Voice input: text input stub (mic → STT pipeline in Inc 2)
- [ ] Explainability: Lily produces structured plan before execution; plan stored in audit log

**Deliverables**:
- Working end-to-end demo: "deploy the app to staging" → Terraform apply → audit log entry
- Architecture docs (this file)
- Patent-ready design documentation

**What this proves**:
- Pipeline Equivalence Principle: AI agent with governance = CI/CD pipeline with safety
- Accessibility story: no Terraform expertise needed by operator
- Audit trail: every action traceable from command to outcome

---

### Increment 2 — Voice + Real Blockchain (3-6 months post Inc 1)

**Goal**: Replace stubs with production-grade components. Full voice pipeline.

**Scope**:
- [ ] Voice capture: mic input → Google Cloud STT → transcript
- [ ] Speaker verification: classical biometrics (SpeechBrain x-vectors or Azure Speaker Recognition)
- [ ] Liveness detection: challenge-response (text prompt, verify response)
- [ ] Session token: JWT minted on auth success, scoped to permission tier
- [ ] Blockchain A: migrate permission store to Hyperledger Fabric
- [ ] Blockchain B: migrate audit log to Hyperledger Fabric audit channel
- [ ] Continuous session auth: behavioral drift detection (pitch/rate monitoring)
- [ ] Sub-agents: Lily spawns specialist agents (Terraform agent, GCP agent, Linux agent)
- [ ] GCP Workload Identity: Lily authenticates to GCP via short-lived federated tokens

**Migration path from Inc 1**:
- Hash-chained SQLite log → Hyperledger: export existing log, hash-verify continuity, import to Fabric
- Static YAML permissions → Hyperledger: enrollment ceremony, sign existing roles onto ledger

---

### Increment 3 — Quantum + Multi-Cloud + Edge (6-18 months post Inc 2)

**Goal**: Differentiated security (twin discrimination, QRNG), edge/air-gapped deployment, multi-cloud.

**Scope**:
- [ ] Quantum kernel speaker verification (Qiskit / PennyLane PQC)
- [ ] HDC voiceprint encoding (D = 2,000–4,000)
- [ ] QRNG challenge generation (IBM Quantum / IonQ cloud API)
- [ ] Twin-pair enrollment protocol + adaptive threshold governance
- [ ] Local/edge deployment: K8s (k3s), local Fabric network, offline voice model
- [ ] Multi-cloud: AWS and Azure tool adapters alongside GCP
- [ ] Additional agents: security scanner, cost optimizer, compliance auditor
- [ ] FedRAMP / NIST 800-53 control mapping (AU, AC families)

---

## 7. Lily Agent Design

### 7.1 Tool Set (Inc 1)

```python
LILY_TOOLS = [
    "linux_exec",        # allowlisted shell commands (ls, ps, df, etc.)
    "gcp_query",         # read-only GCP resource queries
    "terraform_plan",    # generate Terraform plan (no apply)
    "terraform_apply",   # execute approved Terraform plan (Tier 3+)
    "permission_check",  # query Blockchain A for Chris's permissions
    "audit_write",       # append event to Blockchain B
    "request_confirm",   # prompt Chris for confirmation (Tier 3-4)
]
```

### 7.2 Structured Intent Object

Lily must produce this before any execution:

```json
{
  "action": "deploy",
  "target": "app-v2.1",
  "environment": "staging",
  "scope": ["projects/my-project/services/app"],
  "constraints": ["no-production", "no-iam-changes"],
  "estimated_cost": "~$0.05/hr",
  "tier": 2,
  "requires_confirmation": false
}
```

### 7.3 Execution Plan

Lily must produce this before any tool call:

```json
{
  "steps": [
    {"step": 1, "tool": "gcp_query", "action": "verify staging environment exists"},
    {"step": 2, "tool": "terraform_plan", "action": "generate plan for app-v2.1 to staging"},
    {"step": 3, "tool": "terraform_apply", "action": "apply approved plan"}
  ],
  "rollback": [
    {"step": 1, "tool": "terraform_apply", "action": "apply rollback plan to app-v2.0"}
  ]
}
```

The governance gate validates the plan. The audit log records the plan hash. Explainability is inherent: the chain of reasoning is always visible.

### 7.4 The Expert + Apprentice Dynamic

Lily functions as both a capable executor and a learning assistant:
- She explains what she's doing and why (teaching Chris over time).
- She asks clarifying questions when intent is ambiguous.
- She flags when a request exceeds Chris's permissions rather than silently failing.
- She suggests alternatives when a requested action is blocked by policy.

---

## 8. Governance Gate Design

### 8.1 Policy Engine (OPA/Rego)

```
voice_command → intent_object → execution_plan
                                       │
                            ┌──────────▼──────────┐
                            │   Governance Gate    │
                            │                      │
                            │  ┌────────────────┐  │
                            │  │ IAM policy     │  │ ← Blockchain A
                            │  │ enforcement    │  │
                            │  └────────────────┘  │
                            │  ┌────────────────┐  │
                            │  │ Scope          │  │ ← intent constraints
                            │  │ validator      │  │
                            │  └────────────────┘  │
                            │  ┌────────────────┐  │
                            │  │ SOP compliance │  │ ← org runbooks
                            │  │ checker        │  │
                            │  └────────────────┘  │
                            │  ┌────────────────┐  │
                            │  │ Resource       │  │ ← GCP API
                            │  │ existence      │  │
                            │  └────────────────┘  │
                            └──────────┬───────────┘
                                  PASS/FAIL/MODIFY
```

**Key principle**: The governance gate uses a **deterministic rule engine** (OPA/Rego), not an LLM. Lily's hallucinations cannot pass through an LLM-based validator. The gate is architecturally independent from the planning agent.

### 8.2 Guardrails vs. Governance

- **Governance** = the policy framework (what Chris can do, what Lily can plan)
- **Guardrails** = runtime enforcement of that policy (OPA rules, scope constraints, tier checks)
- Guardrails live *inside* governance. They are the teeth of the policy.

---

## 9. Audit Chain (Blockchain B)

Each entry is cryptographically linked to its predecessor (hash of previous entry included in current entry's hash):

```
Entry 1: voice_auth_event
  ├── speaker_id_hash
  ├── confidence_score
  ├── session_token_hash
  └── prev_hash: "genesis"

Entry 2: intent_object
  ├── utterance_hash
  ├── structured_intent (JSON)
  └── prev_hash: hash(Entry 1)

Entry 3: execution_plan
  ├── plan_hash
  ├── plan_json
  └── prev_hash: hash(Entry 2)

Entry 4: governance_result
  ├── rules_evaluated
  ├── pass/fail/modify
  └── prev_hash: hash(Entry 3)

Entry 5+: execution_steps (one per tool call)
  ├── tool_name, tool_input_hash
  ├── tool_output_hash
  └── prev_hash: hash(previous entry)

Entry N: outcome_state
  ├── final_state_hash
  ├── drift_detected: bool
  └── prev_hash: hash(Entry N-1)
```

Inc 1 implementation: SQLite table + SHA-256 hash chain. Inc 2+: Hyperledger Fabric.

---

## 10. Migration Paths

| Component | Inc 1 (Now) | Inc 2 Migration | Inc 3 Migration |
|---|---|---|---|
| Blockchain A | Static YAML file | Hyperledger Fabric enrollment | Add ZK-proof layer for privacy |
| Blockchain B | SQLite hash-chain | Hyperledger Fabric audit channel | Public chain attestation anchors |
| Voice auth | Text input stub | Classical speaker ID (SpeechBrain) | Quantum kernel (Qiskit PQC) |
| Lily agent | Single Claude agent | Lily + specialist sub-agents | Multi-agent mesh with routing |
| Deployment | Local Python | GCP Cloud Run / GKE | + k3s edge / air-gapped |
| Cloud scope | GCP only | GCP primary | GCP + AWS + Azure adapters |
| Confirmation | Text prompt | Voice phrase | QRNG challenge phrase |

---

## 11. Relationship to Existing PE/SRE Practice

VoiTomation does not replace existing tools — it provides a **natural language interface** to them, with governance built in.

| Traditional | VoiTomation equivalent |
|---|---|
| `terraform apply` | "Lily, deploy app-v2.1 to staging" |
| CI/CD pipeline YAML | Lily's execution plan (structured JSON) |
| IAM roles/policies | Blockchain A + Governance Gate |
| CloudTrail / Audit Logs | Blockchain B (dual-path: ledger + cloud audit) |
| Runbook / SOP | OPA/Rego SOP compliance checker |
| On-call expert | Lily (available 24/7, never forgets syntax) |
| "Type DELETE to confirm" | Tier 3-4 voice confirmation |

The **Pipeline Equivalence Principle** (from the patent disclosure, §5.4.1): AI-driven automation is functionally equivalent to deterministic CI/CD pipelines. Same security requirements, different interface. This framing is critical for enterprise/government adoption — it's evolution, not revolution.

---

## 12. Open Questions (tracked)

| # | Question | Priority | Notes |
|---|---|---|---|
| 1 | Quantum circuit topology (IQP vs hardware-efficient ansatz) | Inc 3 | Empirical testing needed |
| 2 | HDC dimensionality (2K vs 4K) for twin discrimination | Inc 3 | Dataset-dependent |
| 3 | Hyperledger Fabric vs public chain + ZK layer | Inc 2 | Depends on deployment context |
| 4 | GCP Speaker ID vs SpeechBrain for Inc 2 voice auth | Inc 2 | Research needed |
| 5 | QRNG provider (IBM Quantum API vs IonQ) | Inc 3 | Cost/availability tradeoff |
| 6 | Governance framework as standalone patent | Any | §10 of disclosure recommends this |
| 7 | GDPR/BIPA compliance for biometric template storage | Inc 2 | Hash-only approach likely sufficient |
| 8 | FedRAMP / NIST 800-53 control mapping | Inc 3 | AU + AC control families |
| 9 | Local/air-gapped deployment requirements | Inc 3 | K8s (k3s) + local Fabric + offline STT |

---

## 13. Repository Structure (planned)

```
VoiTomation/
├── ARCHITECTURE.md          ← this file
├── docs/
│   ├── Technical_Disclosure_v2_Voice_Auth_Governance.docx
│   └── increments/
│       ├── inc1-design.md
│       ├── inc2-design.md
│       └── inc3-design.md
├── voitomation/
│   ├── __init__.py
│   ├── agent/
│   │   ├── lily.py          ← Lily agent core (Claude + tool loop)
│   │   ├── tools/
│   │   │   ├── linux.py     ← allowlisted shell execution
│   │   │   ├── gcp.py       ← GCP resource queries
│   │   │   └── terraform.py ← Terraform plan/apply
│   │   └── intent.py        ← utterance → structured intent
│   ├── auth/
│   │   ├── voice.py         ← voice auth (stub → classical → quantum)
│   │   └── session.py       ← session token management
│   ├── governance/
│   │   ├── gate.py          ← governance gate orchestrator
│   │   ├── policies/        ← OPA/Rego policy files
│   │   └── tiers.py         ← action tier classification
│   ├── ledger/
│   │   ├── blockchain_a.py  ← permission store (YAML stub → Hyperledger)
│   │   └── blockchain_b.py  ← audit log (SQLite → Hyperledger)
│   └── config.py
├── tests/
│   ├── test_agent/
│   ├── test_governance/
│   └── test_ledger/
├── policies/                ← OPA/Rego governance rules
│   ├── iam.rego
│   ├── scope.rego
│   └── sop.rego
├── requirements.txt
└── README.md
```

---

*Architecture version: 0.1 — Inc 1 design*
*Corresponds to: TD-2026-VOX-QAB-001 Rev. 2*
*Status: Pre-patent filing design documentation*
