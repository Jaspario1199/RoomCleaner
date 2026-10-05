# Independent parameter-ledger review — 4 October 2026

Scope: `docs/design_resolution/{unknown_parameters.json,parameter_register.md,measurement_worksheet.md}`, `tools/design_resolution.py`, and sections3/5 of the main resolution plan. This is a review of traceability and closure mechanics, not physical qualification or a claim that every future unknown has been enumerated. No implementation edits by this reviewer.

## Structural check and findings

The original validator executed successfully: **56 groups /240 fields**, unique group/field IDs, source-file existence and acyclic complete work-package coverage. That result establishes an organized index. It did not establish dimensional correctness, complete engineering dependencies or valid evidence of closure.

| ID | Severity | Concrete finding | Required correction / interpretation |
|---|---|---|---|
| PL-01 | High | A synthetic M01 marked closed/validated with `closure_record="placeholder"` and all actual values null was accepted. | Structured closure records, every applicable required field resolved, credible evidence metadata and explicit unresolved-blocker checks. Never describe the original validator as enforcing physical closure. |
| PL-02 | High | Synthetic nonnumeric measured values with empty date/revision/evidence and a negative numeric uncertainty were accepted. | Reject empty metadata, nonfinite/negative uncertainty and incompatible numeric/text structures. Distinguish a requirement/design choice from an instrument measurement. Human review still evaluates evidence validity. |
| PL-03 | High | Acceptance refers to εL/εp/εR/εvision and precision/recall without explicit requirement fields. A measured result cannot pass an undefined threshold. | Predeclare requirements and uncertainty/error allocation before tests. Owner added P01, separate resolution basis/kind, bringing the intermediate ledger to **57 groups /265 fields**. All groups remain unresolved. |
| PL-04 | Medium | The work-package graph is syntactically acyclic but reuses groups at preliminary and integrated stages without identifying closure ownership. W01 references C03/C06/C12 policies while their actual calibrations depend on later hardware; W02 includes final feasible workspace C11; W04 powered torque/feedback depends on safe W05 power. | Treat packages as staged investigation milestones, not assertions that every referenced group closes there. Identify final closure owner/prerequisites; allow preliminary supported fixtures and requirements to precede integrated tests without claiming final qualification. |
| PL-05 | Medium | Transport is a main architecture choice, but the initial C08 records only timing/clock/segment fields. It does not name selected transport, contacts, transceiver/topology or interlock pin allocation. | Explicit structured architecture decision with selected profile/transport, pin/connector contract, termination/topology and link/fault requirements. W05 connector layout depends on this choice; timing validation alone cannot close it. |
| PL-06 | Medium | Protection is discussed in prose but initial E02 does not separately identify available source fault current, fuse time-current/inrush/transient behavior or USB/reverse-polarity protection choices. | Store a referenced protection design/coordination record covering these quantities and test results. Do not infer source/branch coordination from fuse nominal amperes or connector keying. |
| PL-07 | Medium | Vector/matrix/pose/table fields have only generic units, e.g. positions[m], transforms[pose], intrinsic matrix[pixel], planes[m], service sweep[volume]. Dimensional labels alone do not define shapes, axes, conditions or mixed-unit structure. | Require datum/frame, shape/axis order, conditions and evidence type in each resolved record. A plane needs normal convention and offset; a rigid transform needs translation units and rotation convention; calibration tables need independent variables and tested domain. |
| PL-08 | Medium | Mechanically/control-duplicated facts such as M01/C01 outlet locations, M11/C04 payout and M16/C02 mass are linked conceptually but can be independently filled inconsistently. | One authoritative fact/evidence record per revision, referenced by downstream groups; explicit conversion and consistency checks. Per-axis/per-board records must preserve A/B/C/D identity and chosen firmware profile. |
| PL-09 | Low | Source checks establish that a specialist audit file exists; they do not identify source revision, actual consumer or drawing/test result. | Include commit/configuration IDs and exact supplier/model/test evidence references at resolution. Existing source paths are legitimate starting provenance, not proof of a hardware measurement. |

The three invalid examples were tested on deep copies in memory. The actual ledger was not closed or populated with fake measurements.

## Scope and completeness assessment

The ledger covers the important present families: physical frames/finite-body equilibrium, real mass/COM, working and homing cones, ropes/payout/sag, secured switch/return mechanics, spool retention, encoder alignment, printed processes/creep, power/harness/service packaging, four-axis timing and faults, battery/servo, camera pose/age/occlusion, success evidence and procurement states. It is a useful development skeleton.

The count is not a proof that "all unknowns" are closed or listed. New measurements, selected transport, actual supplier revisions and supported-workspace tests will add scoped parameters. Aggregate IDs can describe a family; final data must retain per-axis/per-part identity rather than one ambiguous number for four stations. Human signoff remains necessary for evidence content, meaningful negative tests and compatible assumptions.

## Work-package interpretation

Sections3/5 correctly separate motor angle, rope payout, finite pose, structural reaction, power and vision evidence. The recommended ordering is plausible as an investigation plan. It needs staged completion semantics:

1. W01 freezes architecture/coordinate/requirement contracts; references to later calibration groups do not close their measured values.
2. W02 establishes provisional survey/mass/load envelopes; it does not close final integrated workspace or attitude capability.
3. W03/W04/W05 use restrained prototypes to resolve their respective interfaces and load/power requirements iteratively. Safe provisional power precedes powered mechanical tests; final enclosed thermal qualification follows final geometry.
4. W06/W07/W08 establish structural, execution and clamp evidence with the actual revision.
5. W09 closes integrated pose/length/tension/obstacle limits after upstream groups pass.
6. W10 closes image-specific pose/time and negative pickup/release cases; W11 publishes one consistent released configuration and inventory record.

This staged reading avoids a false all-or-nothing cycle between final enclosure, current/torque tests and mechanical integration. Parameter closure should follow actual blocking group prerequisites, not merely membership in a package.

## Requirements and error budgets

Adding P01 corrects the initial missing-target problem. Targets must remain proposed until chosen; they are not measurements. Allocate the total pose/length/vision error among survey, encoder/winding/line behavior, structural compliance, camera calibration, image/pose time and payload depth/occlusion. The budget should include correlated bias and worst-case bounded terms where appropriate; summing unrelated RMS values is not automatically justified.

For synchronized execution, a first timing term is cable speed×clock/start skew. For moving vision, a first time-association term is relative camera/target speed×pose/frame age. These are partial bounds, not complete error models. Accept a test only with the released configuration, declared working conditions and measured result+uncertainty inside the requirement.

The worksheet correctly distinguishes receipt evidence from performance and leaves unresolved trigger/setup calibration blank. Retain that distinction when adding resolved supplier nominal or user-requirement fields. Do not require meaningless instrument uncertainty for a text architecture decision; its basis is a reviewed design record.

## Release statement

The ledger is an organized, unresolved design/measurement plan. Structural-validator success does not certify dimensional semantics, evidence authenticity, complete engineering dependencies, strength, four-axis control or autonomous camera success.

## Updated guard recheck — 5 October 2026

The revised ledger validates at **57 groups /282 fields** under both ordinary Python and `python -O`. Input guards now raise explicit `ValueError`, so optimization does not remove them. All57 actual groups remain unresolved; no actual measurement or closure was inserted by this review.

Four adversarial deep-copy probes were rejected in both normal and optimized execution:

| Probe | Rejection |
|---|---|
| M01 closed/validated with a string placeholder closure record and null fields | Closure must be structured |
| Nonnumeric outlet measurement with empty metadata | Invalid measured value |
| Numeric measurement with negative uncertainty | Invalid uncertainty |
| M01 structured review record and resolved field values but P01 still open | Blocking groups remain open |

PL-01/02 guard defects are corrected for the tested cases. Structured closure now checks reviewer/date/evidence/dependency review, resolved applicable fields and declared blocking groups. Valid dates, nonblank revisions, finite numeric measurements and nonnegative uncertainties are checked; evidence must reference a file or URL. This is metadata enforcement, not verification that a URL is authoritative or a reviewer actually performed the test.

PL-03 has explicit P01 targets and allocation fields. C08 now names transport/contact count/topology/link rate/interlock pins/clock drift; E02 names supply fault current, fuse curve, inrush, transient, reverse-polarity and USB-isolation records. The package policy explicitly defines staged contributions rather than automatic group closure, addressing the misleading DAG interpretation.

Remaining engineering-review responsibilities are semantic dimensions/array shapes/frame conventions, actual evidence quality, duplicated-fact consistency and the completeness of declared physical blocking dependencies. The revised tool's output correctly claims unit labels, source paths, staged package coverage and closure-record guards—not physical qualification or exhaustive unknown resolution.

## Owner follow-up after principal shape/canonical-alias definitions

Root additionally checked that a malformed4×3 anchor matrix and conflicting nominal effector-mass aliases reject. Numeric negative-uncertainty rejection was repeated on scalar shaft diameter. These checks are recorded in RESEARCH_RESOLUTION_RESULTS_20261004.md; they are owner checks, not new independent physical evidence. Principal vector/matrix shapes now exist, but evidence quality, arbitrary structured curves and complete physical dependency semantics still require engineering review.
