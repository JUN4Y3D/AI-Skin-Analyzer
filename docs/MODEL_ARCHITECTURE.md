# Model architecture and contract 1.0.0

This contract describes a historical baseline and a new **untrained implementation**, not a validated predictor. All outputs are unavailable pending data, model and evaluation review. The historical baseline used an ImageNet-initialized ResNet50 backbone (top excluded), global average pooling, and four dense branches. The new `skin_analyzer.model.build_model` recreates that structure with random initialization, no compilation, and a frozen backbone by default. It only accepts `weights=None`; a future ImageNet option requires separate approval and is currently blocked. The intended input is 224 × 224 RGB with three channels.

| Historical order | Contract name | Batch output shape | Head | Status |
|---|---|---|---|---|
| 1 | skin_type | (N, 3) | 128-unit hidden layer, 3-unit softmax | unavailable; not validated |
| 2 | has_acne | (N, 1) | 64-unit hidden layer, sigmoid | unavailable; no verified negatives |
| 3 | has_dark_circle | (N, 1) | 64-unit hidden layer, sigmoid | unavailable; no verified negatives |
| 4 | skin_age | (N, 1) | 64-unit hidden layer, linear | unavailable; target provenance unknown |

Skin type maps Normal → 0, Dry → 1, Oily → 2. Binary 0 means verified absent, 1 verified present, and -1 missing. Unknown skin type and age -1 are missing. A value of -1 is never a negative. These descriptions do not establish clinical validity.

The version 1.0.0 contract retains the descriptive metadata names in the table. The actual Keras output layer names are `type`, `acne`, `dark`, `age` respectively, in that order. The mapping between the two is explicit and does not change existing metadata.

## Preprocessing compatibility

The proposed standard ImageNet ResNet50 transform accepts RGB float pixels in [0, 255], converts RGB to BGR and subtracts channel means 103.939, 116.779 and 123.680. The historical notebook used RGB divided by 255 instead. A historical checkpoint must not silently switch transforms; determine its actual training history and test equivalence before use. Neither transform proves an existing model works.

`preprocess_image` requires the explicit version `legacy_rgb_0_1` or `resnet50_imagenet_v1`, and supports an RGB image or batch. `preprocess_for_model` also requires an expected version obtained from trusted artifact metadata and rejects mismatches; future training and inference must both call this same boundary. Values in [0,1] can also be valid raw dark pixels, so the code cannot infer prior scaling from pixel values. Selecting and persisting the correct version is the caller's responsibility. The older `preprocess_resnet50` remains available for compatibility.

## Missing labels and future loss design

For each task, construct a per-example validity mask before a compatible per-example loss. Replace invalid targets with a safe placeholder only for loss calculation, then multiply by the mask; sum valid losses and divide by the valid count, not batch size. A zero-valid batch contributes zero for that task and no invalid gradients. Avoid broadcasting between (N,) and (N, 1). Weight normalized task losses with explicit, versioned nonnegative weights; equal weights are only a prospective baseline and changes require justification on independently grouped validation data. Do not train with unverified targets or unapproved data.

The new `masked_losses` primitives instead select only valid rows *before* evaluating cross-entropy or age MSE; they return a numerator and valid count, and use safe division for an empty task. This also avoids masked non-finite prediction values contaminating a loss. Nonmissing categorical or binary labels outside the valid domain fail rather than silently becoming missing. `weighted_task_losses` requires explicit nonnegative weights for every head. Named registered loss functions are provided, but their batch means must not be averaged to claim a dataset-wide mean: accumulate per-task numerators and counts across batches (and replicas if applicable) first. Distributed training semantics are not implemented or verified.

## Serialization and inference

Record contract version, framework versions, input size, pixel scale, color order, preprocessing identifier, ordered named outputs, class mapping, dataset version, provenance and approved-use status. Load only trusted reviewed artifacts with safe deserialization and explicit custom objects as needed; check shapes, names and numerical equivalence with approved golden fixtures. Historical list ordering is [type, acne, dark, age]; do not infer order from dictionary iteration. A mismatch or missing metadata blocks loading. No historical checkpoint has been verified or loaded. The synthetic model, loss, gradient, preprocessing and safe-load tests passed in one TensorFlow 2.16.2 / Keras 3.3.3 environment; they are skipped when TensorFlow is unavailable. The synthetic model round trip currently checks output names and shapes, not numerical prediction equivalence.
