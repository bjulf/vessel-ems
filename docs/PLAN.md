# Research Assistant — Development Plan

## Principles (non-negotiables)

- No experiment runs without explicit approval
- No code changes applied automatically
- LLM reflections never overwrite run facts or metrics
- Paper excerpts are evidence; LLM summaries are interpretation — never mix them
- Chat interface is transport only, never the source of truth
- Every reflection must point to evidence (a run, a paper, or both)

---

## Decision Log

| Decision | Rationale |
|---|---|
| Julia for solver, Python for backend/assistant | Existing codebase; Julia called via subprocess |
| `params.toml` + `history.csv` as run record | Already implemented and sufficient |
| Markdown checkboxes for plan tracking | No external tooling needed, renders on GitHub |
| Paper comparison deferred to Phase 9+ | Advanced reasoning; not load-bearing for early phases |

---

## Phases

### Phase 0 — Principles and schemas
*Goal: lock down what the system must never violate and define run identity.*

- [x] Define what uniquely identifies a run: `(model_variant, solver_settings, dataset, E_init)`
- [x] Git commit hash stamped on every run (`params.toml: git_hash, git_dirty`)
- [x] Run record format defined (`params.toml` + `history.csv`)
- [ ] `docs/system_principles.md` — write out the non-negotiables as a reference document
- [ ] `schemas/experiment_spec.json` — formal schema for what constitutes a reproducible experiment spec
- [ ] `schemas/run_record.json` — formal schema matching current `params.toml` + `history.csv` structure

**Milestone:** Can you describe exactly what inputs are needed to reproduce any stored run?

---

### Phase 1 — Deterministic experiment core
*Goal: make the research engine valuable without any LLM.*

- [x] Run persistence: `params.toml` + `dispatch_results.csv` per run directory
- [x] Run logging: `experiments/history.csv` with key metrics and artifact paths
- [x] Parameter sweep: `experiment.jl` over initial SOC values
- [x] Git hash recorded per run
- [x] Basic dispatch plot: `plot.py`
- [ ] `compare_runs(run_id_a, run_id_b)` — programmatic metric diff + side-by-side plot, no manual notebook work
- [ ] `list_runs(filters)` — filter history by model variant, date, tag, solver status
- [ ] Verify: all plots can be regenerated from stored artifacts alone (no notebook state required)

**Milestone:** Can you reproduce an old run from metadata alone? Can you compare two runs without touching a notebook?

---

### Phase 2 — Proposal and approval boundary
*Goal: stop free-form requests from directly touching the model or launching runs.*

Introduce a strict proposal object:
- experiment purpose
- hypothesis
- changes requested (vs. a named baseline run)
- expected effect
- referenced prior runs
- execution-ready experiment spec
- `requires_approval = true`

- [ ] `validate_experiment_spec(spec)` — checks spec is complete and well-formed
- [ ] `create_proposal_from_template(...)` — structured proposal creation
- [ ] `approve_proposal(proposal_id)` — explicit approval gate
- [ ] `reject_proposal(proposal_id, reason)`
- [ ] Proposal storage in `data/proposals/`

**Milestone:** Can the system represent "test startup penalty vs no startup penalty on the same dataset and same initial SOC" as a formal proposal? Can you inspect the exact diff between baseline and proposed run before approval?

---

### Phase 3 — Reflection and research memory
*Goal: allow discussion and note-taking without corrupting ground truth.*

Three strictly separated memory layers:

| Layer | Contains | Can overwrite? |
|---|---|---|
| Operational | specs, runs, metrics, artifacts | Never by LLM |
| Document | papers, notes, excerpts | Never by LLM |
| Reflective | hypotheses, LLM interpretations, suggested next runs | Only this layer |

- [ ] `store_reflection(run_id, text, linked_evidence)` — every reflection must cite a run or paper
- [ ] `get_reflections_for_run(run_id)`
- [ ] `get_recent_research_context()` — summary of recent runs + attached reflections
- [ ] Reflection storage in `data/reflections/`

**Milestone:** Can the system explain why it suggests a new experiment and cite both prior results and the evidence it drew from?

---

### Phase 4 — Local CLI assistant loop
*Goal: prove the agent logic works before adding any chat interface.*

Build a local command-line interface. Use the LLM only for: intent parsing, proposal drafting, result interpretation. Not for: shell access, code rewrites, autonomous execution.

- [ ] `summarize_recent_runs(n)` — LLM-generated summary over last N runs with metrics
- [ ] `propose_next_experiment(context)` — returns a proposal object, not a direct run
- [ ] `ask_for_approval(proposal_id)` — surfaces proposal for review before anything executes
- [ ] `return_result_summary(run_id)` — after completion, return summary + plot paths
- [ ] `interfaces/cli.py` — thin wrapper over backend commands

**Milestone:** You can type "Summarize the last 5 runs and propose one follow-up test." The system returns a grounded proposal and an approval prompt. Nothing runs until you say yes.

---

### Phase 5 — Typed command layer
*Goal: constrain the assistant to a small, safe, validated action space.*

Define typed commands with strict schemas (Pydantic-style, even if not using PydanticAI as a full framework):

| Command | Key fields |
|---|---|
| `propose_experiment` | objective, changed_constraints, changed_parameters, dataset, rationale, reference_runs |
| `run_experiment` | approved_proposal_id |
| `summarize_run` | run_id |
| `plot_metric` | run_id, metric |
| `compare_runs` | run_id_a, run_id_b |
| `search_runs` | filters |
| `show_current_model_config` | — |

- [ ] Pydantic schemas for all commands
- [ ] `command_router.py` — validates and dispatches commands
- [ ] No natural-language request ever directly executes backend logic without going through a validated command

**Milestone:** Every LLM-generated action is a validated command object. Malformed or incomplete commands are rejected before execution.

---

### Phase 6 — Chat interface (OpenClaw / Discord)
*Goal: make the system accessible from chat without changing the core architecture.*

OpenClaw does three things only: receive message → call typed backend commands → return plots, summaries, approval prompts. It is not the database, the run engine, or the retrieval layer.

- [ ] `interfaces/openclaw_adapter.py` — maps chat messages to typed commands
- [ ] Initial supported chat actions:
  - "Show last 5 runs"
  - "Propose an experiment varying startup penalty"
  - "Run the approved proposal"
  - "Plot SOC and fuel for run `<run_id>`"
- [ ] Discord channel setup (single channel first, not WhatsApp)

**Milestone:** Full loop through chat: request → grounded proposal → approval → execution → result delivery. If chat breaks, local CLI still works independently.

---

### Phase 7 — Bounded file and browsing actions
*Goal: let the assistant inspect repo files and result artifacts without becoming unsafe.*

Safe actions only:
- [ ] `read_file(path)` — approved directories only
- [ ] `search_file(path, query)` — grep/search within a file
- [ ] `summarize_file(path)` — LLM summary of a config or result file
- [ ] `read_artifact(run_id, artifact_name)` — result CSVs, plots

Deferred (never without explicit approval workflow):
- Edit solver code
- Refactor model files
- Run arbitrary shell commands
- Modify git branches

**Milestone:** The assistant can answer "Which constraints are active in the current model config?" by reading the file, not from memory.

---

### Phase 8 — Paper and result retrieval
*Goal: ground the assistant in literature before it discusses model implications.*

Two retrieval stores:

**Papers store:** paper metadata, chunked text, section titles, equation-adjacent text, tags (`battery_model`, `unit_commitment`, `startup_cost`, `SFOC`, `DC_microgrid`)

**Runs store:** run summaries, plots, metrics, manual notes, proposal histories

- [ ] Ingest core reference papers (PDF parsing, chunking, tagging)
- [ ] `search_papers(query, tags=None)`
- [ ] `search_runs(query_or_filters)`
- [ ] `find_runs_similar_to_spec(spec)`

**Milestone:** Ask "What startup cost formulations appear in the literature?" The system returns cited chunks, not vague prose.

---

### Phase 9 — Paper-to-model comparison
*Goal: ground model comparison in evidence before drawing conclusions.*

This is the most advanced reasoning phase. Deferred until retrieval (Phase 8) is solid.

- [ ] `compare_current_model_to_paper(paper_id)` — structured diff of modelling elements
- [ ] Every comparison output must separate: cited paper excerpt | current model element | gap/difference
- [ ] No vague prose — all claims must be traceable to a specific chunk or run

**Milestone:** Ask "What is missing in my current formulation compared with the COMPEL 2021 paper?" System returns cited chunks plus a structured difference list.

---

### Phase 10 — Semi-automated research loop and workflow orchestration
*This phase marks the start of a larger project milestone. Scope and framework choices to be decided closer to this point.*

*Candidate frameworks: LangGraph, PydanticAI, or custom lightweight orchestration — to be evaluated based on actual workflow complexity at the time.*

A full bounded research iteration:
1. Retrieve relevant past runs
2. Retrieve relevant papers
3. Summarize current state
4. Propose one next experiment
5. Ask for approval
6. Run experiment
7. Generate plots
8. Store reflection linked to evidence

Open questions for this phase:
- [ ] Is resumable multi-step state actually needed, or is request-response still sufficient?
- [ ] Does branching logic justify a graph framework (LangGraph) or is Pydantic validation (PydanticAI) enough?
- [ ] What does a "research iteration checkpoint" look like in this codebase?

**Milestone:** The assistant conducts one bounded scientific iteration without losing state or inventing unsupported claims.

---

### Phase 11 — Code-change assistant (optional)
*Goal: allow the system to draft model modifications without directly changing core code.*

Pattern:
1. Assistant drafts patch proposal
2. You inspect diff
3. You approve
4. Patch applied to feature branch only
5. Tests run, results logged

- [ ] `draft_patch(description, target_file)` — returns a diff, never applies it directly
- [ ] Patch applied only after explicit approval, to a feature branch
- [ ] Main model files never mutated without review

**Milestone:** System produces a code patch for adding a new objective term, but execution depends entirely on your review and approval.

---

## Out of scope

- Arbitrary repo-wide edits or shell access
- Autonomous experiment execution without approval
- LLM writing directly to operational or document memory layers
- WhatsApp interface (adds friction, less transparent debugging)
- Week-by-week timeline (milestone gates used instead)
