# Model interpretation and limitations

## Intended use

AI Skin Analyzer 2.0 is a private educational and portfolio research interface. It demonstrates careful local application engineering around experimental computer-vision artifacts. It is not intended for diagnosis, treatment, triage, product recommendation, identity inference, age verification, or decisions about people.

## Skin-type component

The fitted ResNet50 returns scores ordered `Dry`, `Normal`, `Oily`. These labels are provisional project categories. The model has not measured sebum, hydration, barrier function, or another physiological reference standard. Softmax values are not calibrated confidence.

The approximately 78.90% result came from 109 development images that were examined during development. It is not an independent test estimate and must not be described as clinical accuracy.

## Age-like component

The ridge component estimates an unresolved historical numeric label. Its development MAE was approximately 5.136 label units versus a constant-mean baseline of 6.553. The underlying construct and annotation provenance are not verified. The output must not be described as chronological, biological, or skin age.

## Acne and dark-circle components

These components compare a normalized image embedding with fitted positive-reference embeddings. They report top-k mean cosine similarity and a positive-reference development benchmark. The historical labels do not contain verified negative examples, so the components cannot support sensitivity, specificity, disease probability, or Yes/No classification.

The reported positive-reference coverages of approximately 96.0% and 88.3% are not detection accuracies.

## Data limitations

- Original sources, consent scope, license terms, and annotation provenance remain unresolved.
- Exact duplicates crossed historical splits, and some duplicate groups had conflicting labels.
- Reliable subject identifiers are unavailable; subject-independent evaluation cannot be guaranteed.
- Age meaning is unresolved.
- Normal/Dry/Oily is not a validated clinical taxonomy and must not be confused with Fitzpatrick phototype.
- Acne and dark-circle labels lack genuine verified negatives.
- No independent final holdout supports product or clinical claims.

## Input sensitivity

Predictions may change with crop, pose, illumination, camera processing, blur, cosmetics, occlusion, compression, background, and skin-tone representation. The application now requires automatic face-crop inference, while the models were developed largely with full-image preprocessing. This is an unevaluated input-distribution change and must not be described as improving accuracy.

OpenCV Haar-cascade detection is heuristic. It can miss faces and detect nonfaces. Analysis requires exactly one detection, exposes the analyzed crop in results, and produces no output when detection is missing or ambiguous.

## Distribution limitations

The authorized trained checkpoint, fitted age parameters, and positive-reference embeddings are distributed separately through the versioned GitHub model release, not through Git history. Original facial photographs, source manifests, datasets, and review records remain excluded. Permission to redistribute the inference package does not establish clinical validity or independently verify the original dataset provenance.
