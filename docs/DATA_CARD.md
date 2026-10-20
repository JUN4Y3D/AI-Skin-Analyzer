# Data card — restricted, not approved for training

The existing audit reports 2,400 images, with 1,680 / 360 / 360 in train / validation / test. Sources are mixed or unknown; licenses, consent, minor status, annotation methods and redistribution rights remain unverified. No public dataset is supplied. The private audit detected exact duplicates across splits and conflicting labels; subject independence is not established.

Both binary fields contain positives and missing values but no verified negatives, so present-versus-absent learning and meaningful specificity cannot be supported. Age is a numeric legacy field whose target and provenance are unknown. Skin type mapping is a project convention, not a medically validated taxonomy. Local recovery and provenance reports contain detailed evidence; do not publish without review.

Before training: document source permissions and consent, review duplicates and conflicts privately, adopt an annotation protocol including unknown/uncertain states, establish group-disjoint splits including known derivatives and subjects, and approve a versioned dataset. If subject identifiers are unavailable, subject independence remains unprovable. Never distribute private images, manifests, or filenames by default.
