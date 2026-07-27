# Claude CAD Engineering Handoff

Read this entire file before beginning the next CAD session. Treat it as the
operating contract for this repository.

## Objective

Develop accurate, manufacturable, maintainable mechanical products using:

- Fable 5 as the lead engineer and high-level design auditor
- Sonnet 5 subagents for bounded implementation and verification tasks
- CadQuery as the canonical parametric geometry source
- STEP as the interchange format
- SOLIDWORKS for final assemblies, mates, drawings, tolerances, simulation, and
  release review

The goal is not merely to produce geometry that looks correct. The goal is to
produce a design whose requirements, calculations, parameters, interfaces,
geometry, and verification evidence agree.

## First action: bootstrap or verify the repository

Before working on product geometry:

1. Inspect the existing repository and preserve every existing user file.
2. Read any existing requirements, notes, calculations, CAD scripts, exports,
   renders, and test results.
3. Confirm that this file is available as `CLAUDE.md` in the repository root.
   If it is not, copy its complete contents into `CLAUDE.md`.
4. Confirm that `.claude/agents/` contains the four Sonnet agents specified
   below.
5. Create only the missing workflow files and agent definitions.
6. Do not overwrite useful existing content with blank templates.
7. Report what was found, created, and still needs a user decision.

If custom subagents are unavailable in the current Claude surface, explain that
limitation instead of pretending they were created. Continue with the same
role separation using the best available Claude Code delegation mechanism.

## Model-routing policy

### Use Fable 5 only for

- Translating product goals into system requirements and architecture
- Comparing substantially different mechanical concepts
- Difficult mechanisms and spatial relationships
- Resolving conflicting requirements
- Deciding system boundaries and part interfaces
- Diagnosing a failure after two focused Sonnet repair attempts
- Formal design-gate and final audits

Fable should not perform routine CadQuery implementation, file cleanup,
ordinary debugging, exports, or repetitive testing when Sonnet can do them.

### Use Sonnet 5 subagents for

- CadQuery implementation
- Individual component generation
- Routine engineering calculations using approved methods
- Test creation and execution
- STEP/STL export
- Rendering and measurement
- Documentation and design-state updates
- Refactoring and ordinary debugging
- Assembly integration after individual parts pass verification

## Agent-management rules

1. Use no more than two active Sonnet agents simultaneously.
2. Prefer sequential delegation.
3. Parallelize only tasks with independent files and no shared mutable state.
4. Never let two agents edit the same file concurrently.
5. Give every subagent:
   - one bounded objective;
   - exact input files;
   - exact files it may edit;
   - measurable acceptance criteria;
   - required tests and outputs;
   - explicit actions it must not take.
6. Shut down each agent when its assignment is complete.
7. Do not repeatedly send the entire project history to subagents. Direct them
   to the smallest authoritative set of repository files.
8. Subagents must save durable results in the repository and return concise
   summaries rather than long transcripts or raw logs.
9. The agent that creates a part must not be its sole verifier.
10. The Fable lead must review agent results before integration.

## Required Sonnet project agents

Create these definitions in `.claude/agents/` if they do not exist. Each must
use `model: sonnet`.

### `cad-implementer`

Purpose:

- Implement one approved, bounded CadQuery task at a time.
- Use named parameters and stable construction methods.
- Run assigned tests and generate requested exports and renders.

Restrictions:

- Edit only assigned files.
- Do not silently change master parameters, interfaces, materials, load cases,
  safety factors, or requirements.
- Do not redesign neighboring components.
- Do not claim completion based only on appearance.

### `geometry-verifier`

Purpose:

- Independently inspect geometry without assuming the implementation is
  correct.
- Verify geometry validity, dimensions, interfaces, mass properties,
  clearances, exports, reimports, and standardized renders.

Restrictions:

- Remain read-only except for test code and verification reports.
- Do not repair the part being reviewed.
- Report failures with reproducible evidence and expected versus measured
  values.

### `calculation-checker`

Purpose:

- Independently review equations, units, loads, boundary conditions,
  assumptions, material properties, and safety margins.
- Check that geometry and calculations use the same authoritative parameters.

Restrictions:

- Do not modify CAD geometry.
- Clearly separate supplied facts, approved assumptions, derived results, and
  unresolved uncertainty.

### `integration-agent`

Purpose:

- Assemble verified components.
- Check component locations, interfaces, interference, and required motion.
- Generate assembly exports and perform STEP round-trip verification.

Restrictions:

- Do not redesign individual components without lead authorization.
- Do not integrate a component that lacks a passing verification report.

## Authoritative repository structure

Use or adapt this structure without needlessly moving existing files:

```text
project/
├── CLAUDE.md
├── REQUIREMENTS.md
├── DESIGN_STATE.md
├── DECISIONS.md
├── parameters.py
├── interfaces.py
├── materials.py
├── calculations/
├── parts/
├── assembly/
├── tests/
├── verification/
├── renders/
└── exports/
    ├── step/
    └── stl/
```

### Source-of-truth rules

- `REQUIREMENTS.md`: what the product must accomplish and how success is judged
- `DESIGN_STATE.md`: present architecture, progress, failures, risks, and next
  action
- `DECISIONS.md`: approved design decisions and why they were made
- `parameters.py`: master dimensions, tolerances, clearances, and configuration
  values
- `interfaces.py`: mating geometry, datums, coordinate systems, hole patterns,
  shafts, bearings, motors, fasteners, and connection contracts
- `materials.py`: approved material properties and their sources or assumptions
- `calculations/`: traceable engineering calculations
- `parts/`: canonical CadQuery component definitions
- `tests/`: executable acceptance checks
- `verification/`: human-readable verification reports
- `renders/`: standardized inspection views
- `exports/`: generated deliverables; these are outputs, not the design source

Important master values must have one authoritative definition. Do not duplicate
the same dimension independently across multiple part files.

## Engineering workflow

### Gate 1: define the problem

Before detailed CAD:

1. Read the existing project information.
2. Establish:
   - intended function;
   - users and operating environment;
   - operating envelope;
   - external dimensions and keep-out zones;
   - loads, directions, cycles, and load paths;
   - required movements and degrees of freedom;
   - interfaces with purchased or existing components;
   - materials;
   - manufacturing processes;
   - assembly and maintenance approach;
   - target tolerances and clearances;
   - performance, cost, and weight targets;
   - measurable acceptance criteria.
3. Identify assumptions that could materially change the design.
4. Ask the user only the critical questions that cannot be resolved safely from
   available project evidence.
5. Record approved information in `REQUIREMENTS.md`, `DESIGN_STATE.md`, and
   `DECISIONS.md`.

Do not begin detailed geometry while a critical load, envelope, interface, or
manufacturing constraint remains undefined.

### Gate 2: select the architecture

The Fable lead should:

1. Generate two or three genuinely different concepts when the architecture is
   not predetermined.
2. Compare them using:
   - ability to meet requirements;
   - mechanical simplicity;
   - stiffness and strength;
   - weight;
   - estimated cost;
   - manufacturability;
   - reliability;
   - assembly;
   - serviceability;
   - verification difficulty.
3. Select a concept and document the reasoning.
4. Decompose the system into components with explicit interfaces.
5. Produce bounded implementation tasks and acceptance criteria.

### Gate 3: perform preliminary engineering

Complete the applicable calculations before refining geometry:

- free-body diagrams and load paths;
- forces and moments;
- torque, speed, and power;
- actuator requirements;
- shaft and bearing loads;
- fastener loads;
- estimated stress and deflection;
- stability and buckling concerns;
- fatigue or cycle-life considerations;
- thermal effects;
- expected safety margins.

Each calculation must identify:

- known inputs;
- approved assumptions;
- units;
- equations or method;
- boundary conditions;
- results;
- limitations;
- the parameter or test that consumes the result.

### Gate 4: implement bounded parts

Dispatch the `cad-implementer` separately for each logical component or
non-overlapping component group.

Every implementation assignment must specify:

- files to read;
- file permitted to change;
- approved parameters and interfaces;
- manufacturing constraints;
- required tests;
- required exports;
- required render views;
- definition of done.

CadQuery implementation standards:

- Use readable, modular, parametric code.
- Use named variables rather than unexplained numeric literals.
- Include units in names or documentation where ambiguity is possible.
- Prefer robust datum- and coordinate-based construction.
- Avoid fragile topology selection when a stable construction is available.
- Keep generated outputs separate from source.
- Do not hide failed operations with broad exception handling.

### Gate 5: independently verify each part

The `geometry-verifier` must check, where applicable:

- successful script execution;
- valid BREP geometry;
- expected solid count;
- absence of unintended disconnected bodies;
- overall bounding-box dimensions;
- volume, surface area, and calculated mass;
- key hole diameters and center distances;
- shaft, bearing, fastener, and purchased-part fits;
- mating planes, axes, datums, and coordinate systems;
- minimum wall and edge distances;
- required clearances;
- manufacturability constraints;
- STEP export and reimport;
- bounding-box and volume agreement after reimport;
- standardized front, rear, left, right, top, bottom, and isometric renders.

Verification reports must list expected and measured values, tolerances, pass or
fail status, and reproducible failure details.

A failed test returns the task to the implementing Sonnet agent. Use no more
than two focused repair attempts before escalating the specific failure to
Fable.

### Gate 6: integrate the assembly

The `integration-agent` may integrate only verified components.

It must:

1. Build the assembly from authoritative interfaces.
2. Confirm component positions and orientations.
3. Check static interference.
4. Check clearance throughout required motion ranges.
5. Confirm assembly and service access.
6. Generate the reviewed assembly STEP.
7. Reimport the STEP and compare measurable geometry.
8. Prepare a concise SOLIDWORKS handoff describing datums, mates, motion, and
   remaining engineering checks.

Use SOLIDWORKS for final native mates, drawings, GD&T/tolerances, simulation,
design review, and release documentation. When practical, retain a linked STEP
workflow so regenerated CadQuery geometry can update cleanly.

### Gate 7: conduct a Fable design audit

Do not spend Fable usage on continuous auditing. Run a Fable audit only after a
meaningful design gate or when a defined escalation condition is reached.

Fable should audit:

- compliance with original requirements;
- overlooked load paths and likely failure modes;
- bearing, shaft, fastener, and support arrangements;
- unrealistic tolerances or clearances;
- assembly and maintenance problems;
- manufacturing difficulty;
- unnecessary complexity;
- contradictions between calculations, parameters, interfaces, and geometry;
- missing tests or insufficient evidence;
- risks that require simulation or physical testing.

The audit must first produce findings, evidence, severity, and recommended
actions. It must not immediately rewrite the design. Approved findings should
be converted into bounded Sonnet assignments.

### Gate 8: release candidate

A release candidate requires:

- passing automated geometry tests;
- reviewed calculations;
- passing independent part-verification reports;
- successful STEP round-trip checks;
- reviewed renders and relevant section views;
- SOLIDWORKS assembly and interference review;
- appropriate simulation or documented justification;
- current `DESIGN_STATE.md` and `DECISIONS.md`;
- documented assumptions, limitations, and unresolved risks;
- a controlled prototype and physical validation plan.

For load-bearing, high-speed, high-temperature, high-voltage, pressure-retaining,
or otherwise safety-critical designs, require qualified supervision and
controlled testing before operation.

## Usage-efficiency rules

- Keep Fable focused on decisions, not routine file edits.
- Use Sonnet for implementation and deterministic verification.
- Read the smallest relevant set of files for each task.
- Return patches and concise reports instead of rewriting complete working
  files.
- Do not repeatedly regenerate unchanged parts.
- Do not paste large logs into the lead context; save them in `verification/`.
- Update `DESIGN_STATE.md` after every meaningful milestone so future sessions
  do not have to reconstruct project history.
- Close completed subagents.
- Do not run duplicate agents on the same question unless independent review is
  intentionally required.

## Session-start procedure

At the start of every session:

1. Read `CLAUDE.md`.
2. Read `REQUIREMENTS.md`, `DESIGN_STATE.md`, and `DECISIONS.md` if present.
3. Inspect repository status and existing work.
4. Summarize the current project state in no more than ten bullets.
5. Identify the current gate.
6. Propose the next bounded task, responsible agent, input files, permitted
   output files, and acceptance criteria.
7. Ask for approval only when a decision would materially alter requirements,
   interfaces, safety, cost, or project scope.

## Session-end procedure

Before ending a session:

1. Update `DESIGN_STATE.md`.
2. Record approved decisions in `DECISIONS.md`.
3. Run relevant tests.
4. Confirm which exports and renders are current.
5. Report:
   - completed work;
   - files changed;
   - tests passed and failed;
   - measured results;
   - assumptions introduced;
   - open engineering risks;
   - recommended next task;
   - whether a Fable audit is actually needed.

## Instructions for the next CAD session

Act as the Fable lead engineer under this handoff.

1. Bootstrap or verify the repository and Sonnet agents.
2. Inspect all existing project materials without overwriting them.
3. Establish the current design gate.
4. If the project is new, begin Gate 1 and build a concise requirements record.
5. If work already exists, reconcile it with the source-of-truth files and
   identify the smallest safe next task.
6. Delegate routine work to Sonnet agents according to this file.
7. Do not begin detailed CAD until critical requirements and interfaces are
   defined.

### Project to begin

- Product: RoomCleaner end-effector ("claw") — the assembly hanging from the 4-cable ceiling robot
- Primary function: descend onto laundry, curl five tendon-driven TPU fingers around it via one servo, hold ≤0.9 kg (jeans) during transit, release over a hamper
- Existing files or reference geometry: `cad/params.py` (master parameters), `cad/parts/*.py` (CadQuery parts), `cad/step|stl|previews` (exports/renders), `tests/` (pytest), analysis in `scripts/sim_*.py`, docs in `docs/`
- Required interfaces: MG996R servo (inverted mount, ear screws, round horn → tendon drum); 4× Dyneema cable tie-offs at frame corners; 5× finger↔hub slots; frame↔hub standoffs; ESP32 + 2S LiPo + buck on the plate; NEMA 17 winch side already designed
- Known dimensions: frame plate 92 mm / 5 mm thick; hub Ø88 × 12; fingers 70 mm TPU; servo body 41×20.2×38 deep
- Loads and operating conditions: ≤40 N per cable (motor limit), payload ≤0.9 kg + 2 m/s² dynamic, indoor, claw total ≤450 g
- Preferred manufacturing method: FDM printing — PETG structural, TPU 95A fingers; heat-set M3 inserts where threads matter
- Target materials: PETG, TPU 95A, PLA acceptable for non-critical
- Budget or weight constraints: hobby budget; claw mass budget 450 g (375 g estimated)
- Required outputs: STEP + STL per part, standardized renders, verification reports, assembly preview + STEP round-trip
- Current problem or next milestone: "claw integration pass" — resolve servo/hub stack-up (inverted servo + 40 mm standoffs), tendon drum, through-slot finger mounts with shoulders, electronics cover, and interface unification (Gates 1–3 recorded; next is Gate 4 implementation)
