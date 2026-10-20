# Dataset eligibility policy

## Purpose and scope

This policy is the gate for any facial-image data considered for the AI Skin Analyzer. It applies source-lot by source-lot before annotation, split construction, training, evaluation, model distribution, or raw-data release. It is not legal advice; ambiguous rights or consent require qualified review. Public availability, technical accessibility, or academic labeling does not by itself authorize facial-analysis machine learning.

A **source lot** is the smallest group of files governed by one traceable acquisition event, provider, version, license/terms set, consent or lawful basis, and annotation provenance. If those facts differ, create separate lots. Record decisions in the private source-lot register; never place sensitive filenames, subjects, access credentials, or consent documents in public materials.

## Required decision states

| State | Meaning | Training | Model distribution | Raw-image redistribution |
|---|---|---|---|---|
| `verified_allowed` | Authoritative evidence covers the intended facial-image ML use and every applicable condition is satisfied; each distribution permission is recorded separately | Allowed within recorded scope | Only if explicitly permitted | Only if explicitly permitted |
| `verified_training_only` | Evidence permits controlled training/evaluation but prohibits or does not grant raw-image redistribution; model distribution has an explicit, separately recorded answer | Private, controlled use only | As separately documented; unknown means blocked | Prohibited |
| `conditional` | A potentially eligible lot has identified conditions not yet satisfied, such as attribution, access controls, geography, deletion duties, consent scope, or minor safeguards | Blocked until all conditions are evidenced and implemented | Blocked | Blocked |
| `unresolved` | Source, rights holder, applicable terms, consent/lawful basis, version, file mapping, or permitted use cannot be documented | Blocked | Blocked | Prohibited |
| `rejected` | Authoritative terms, consent scope, provenance reliability, privacy risk, or required safeguards are incompatible with the intended use | Prohibited | Prohibited | Prohibited |

Unknown provenance always defaults to `unresolved`. A decision applies only to the reviewed source lot and evidence version; it does not transfer to reposts, later releases, derivatives, or similarly named files.

## Evidence needed for promotion

To move a lot out of `unresolved`, the private record must contain:

1. A stable source ID and a defensible mapping from every local item to exactly one lot, without relying only on its filename or appearance.
2. The authoritative provider/rights holder, canonical acquisition page or documented direct acquisition, dataset/version or acquisition date, and an original archive/manifest record where available.
3. A saved, dated copy of the license and applicable terms from the authoritative source, including attribution, field-of-use, commercial/portfolio, geography, retention, deletion, derivative, and access-control clauses.
4. Evidence that the terms permit the intended facial-image analysis tasks—not merely download, research in general, or publication of photographs.
5. Consent or another applicable lawful basis, including whether acne-like features, periorbital appearance, and age-related annotation/inference are within scope; withdrawal/takedown handling must be documented.
6. A minor policy. If minors may be present, the lot needs documented authorization and the applicable guardian/assent and use restrictions. Filename tokens or predicted ages are not proof of age.
7. Separate decisions for private training, model/weight distribution, and raw-image/metadata redistribution. Silence is `unknown`, therefore blocked.
8. Annotation provenance: label source, construct definitions, rubric version, annotator qualifications, date, uncertainty handling, adjudication, transformations, and lineage to the source lot.
9. Reviewer, review date, outstanding conditions, and evidence locations. Evidence must remain private and access-controlled.

`conditional` may be promoted only when each stated condition has objective evidence of completion. `verified_training_only` requires affirmative training permission and adequate privacy/consent evidence; it is not a compromise state for uncertain rights. `verified_allowed` still requires permission flags to be consulted for each contemplated release action.

## Annotation eligibility and definitions

Only items mapped to eligible lots may enter a separately approved annotation workflow. Preserve legacy labels unchanged; create versioned overlay annotations with source lot, rubric version, annotator, timestamp, confidence, and adjudication fields. Never convert `-1`, `Unknown`, missing, or uncertain into a negative.

- **Skin type:** first define a defensible observable construct and assessment conditions; the existing Normal/Dry/Oily taxonomy is not Fitzpatrick skin type and is not yet clinically validated. Allowed states are one rubric-defined class, `unknown` (no usable label/evidence), `uncertain` (evidence is ambiguous), and `unassessable` (quality/occlusion/lighting prevents judgment). Multi-label or mixed presentations require an explicit rule rather than forced classification.
- **Acne-like visible features:** `positive` means one or more rubric-defined visible features are present in the specified facial region at the assessment threshold; `negative` means the region is assessable and none are present; `uncertain` means a visible feature cannot be confidently distinguished; `unknown` means no valid review exists; `unassessable` covers inadequate visibility. It is a visual research label, not a diagnosis.
- **Periorbital darkening:** `positive` means rubric-defined visible darkening is present in an assessable periorbital region; `negative` means the region is assessable and the defined feature is absent; `uncertain`, `unknown`, and `unassessable` have the same evidence distinctions above. Lighting, shadows, makeup, occlusion, camera processing, and skin-tone variation require explicit rubric guidance.
- **Skin age:** disabled for training unless the owner approves one precise target (for example, verified chronological age at capture versus a separately defined visual construct), trustworthy source evidence, units, capture date relationship, label uncertainty, lawful/consented use, and an evaluation protocol. Filename-derived numbers and apparent age guesses are insufficient. If these requirements are unmet, retain `unknown` and exclude the age loss.

Every task needs representative, independently reviewed positive and negative examples where applicable, inter-rater/adjudication rules, quality controls, and a documented missing/uncertain policy. Annotation approval does not authorize training; dataset eligibility, grouping, split, and evaluation gates remain separate.

## Duplicate and grouping policy

Use a private overlay; never rewrite the legacy manifests in place.

- **Exact content:** byte-identical files are confirmed exact duplicates. Assign a stable duplicate-group ID, link all source-lot records, and keep the entire group in one future split. Conflicting labels are quarantined for evidence-based adjudication; do not use `max`, majority vote, or filename inference automatically.
- **Confirmed derivative:** after an authorized private review establishes crop, resize, compression, color, watermark, or augmentation lineage, assign a derivative-family ID and keep the family together. Record the evidence and reviewer without inferring identity.
- **Similarity candidate:** perceptual-hash or naming heuristics are triage signals only. Mark `unresolved_candidate` until reviewed; do not merge, discard, relabel, or infer that different facial images show the same person.
- **Subject grouping:** use a subject ID only if it comes from reliable, authorized source metadata. Do not use face recognition or infer identity from filenames or appearance. Without a reliable subject key, subject-disjoint evaluation cannot be guaranteed and must be disclosed.

## Replacement-dataset fallback

If the legacy collection cannot be mapped to adequately documented lots, reject it for training and obtain a replacement under a separately approved acquisition plan. The replacement must provide authoritative permission for the exact facial-analysis ML use, consent or another reviewed lawful basis, withdrawal and retention processes, robust minor safeguards, reliable source/version/file lineage, and usable subject or collection grouping where lawfully available. It must have predeclared annotation definitions, both verified positive and negative binary examples, unknown/uncertain states, sufficient independent groups for validation and a final holdout, and representation/quality information needed to assess limitations. Raw-data and model-distribution permissions must be recorded separately; redistribution should remain prohibited unless affirmatively granted.

## Gate for Phase 5B

Phase 5B may begin only after the owner supplies documentary evidence for at least one source lot, a reviewer records an eligibility decision, affected local items can be mapped without guessing, and the intended annotation/review scope is approved. If no lot clears that gate, proceed only with a replacement-dataset acquisition specification—no download, annotation, resplitting, or training.
