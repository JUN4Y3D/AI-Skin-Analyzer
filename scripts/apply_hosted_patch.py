"""Make one additive change to the existing artifact verification logic."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'app/inference/artifacts.py'
text=p.read_text(encoding='utf-8')
old='''    for relative, skin_key, component_key in provenance:
        actual = sha256(_regular_file(root / relative, "private provenance file"))
        if actual != skin_metrics.get(skin_key) or actual != component_metrics.get(component_key):
            raise ValueError("Dataset provenance changed since model fitting")'''
new='''    attestations = None
    for relative, skin_key, component_key in provenance:
        source = root / relative
        if source.is_file() and not source.is_symlink():
            actual = sha256(_regular_file(source, "private provenance file"))
        elif os.environ.get("AI_SKIN_HOSTED_INFERENCE") == "1":
            if attestations is None:
                proof = _regular_file(root / "reports/private/hosted_provenance_sha256.json", "hosted provenance attestation")
                attestations = json.loads(proof.read_text(encoding="utf-8"))
                if not isinstance(attestations, dict) or set(attestations) != {entry[0] for entry in provenance}:
                    raise ValueError("Invalid hosted provenance attestation")
            actual = attestations.get(relative)
            if not isinstance(actual, str) or len(actual) != 64:
                raise ValueError("Invalid hosted provenance digest")
        else:
            raise ValueError("Missing or unsafe private provenance file")
        if actual != skin_metrics.get(skin_key) or actual != component_metrics.get(component_key):
            raise ValueError("Dataset provenance changed since model fitting")'''
if new in text:
    print('Artifact loader already patched')
else:
    if text.count(old)!=1:
        raise RuntimeError('Artifact loader differs from audited version; aborting rather than rewriting it')
    if 'import os\n' not in text:
        text=text.replace('import json\n','import json\nimport os\n',1)
    p.write_text(text.replace(old,new),encoding='utf-8')
    print('Patched artifact loader for hosted attestation mode; local checks unchanged')
