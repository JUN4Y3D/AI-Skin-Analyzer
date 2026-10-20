"""Package private inference artifacts OUTSIDE the Git checkout for Railway upload."""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path
from app.config import AppConfig
from app.inference.artifacts import load_artifacts, sha256

MANIFESTS = (
    'reports/private/phase6d_review_purged_skin_type_manifest.csv',
    'reports/private/phase6c_candidate_derivative_review.csv',
)

def copy(source, destination, root):
    if source.is_symlink() or not source.is_file() or root not in source.resolve().parents:
        raise ValueError(f'Missing or unsafe file: {source.name}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

def prepare(root, target):
    root = root.resolve(strict=True)
    target = target.expanduser().resolve()
    if target == root or root in target.parents or target in root.parents:
        raise ValueError('Target must be outside the Git working directory')
    if target.exists():
        raise ValueError('Refusing to overwrite an existing deployment directory')
    config = AppConfig(project_root=root)
    bundle = load_artifacts(root, config.skin_run, config.components_run)
    relative = Path('reports/private/phase6_training_runs')
    required = [
        bundle.model_path,
        root/relative/config.skin_run/'development_metrics.json',
        root/relative/config.components_run/'prototype_metrics.json',
        root/relative/config.components_run/'age_like_ridge.npz',
        root/relative/config.components_run/'acne_positive_reference.npz',
        root/relative/config.components_run/'dark_circle_positive_reference.npz',
    ]
    try:
        target.mkdir(parents=True)
        shutil.copytree(root/'app', target/'app', ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
        for name in ('server.py','Dockerfile','requirements.txt'):
            copy(root/'deploy/backend'/name, target/name,root)
        for path in required:
            copy(path, target/'private_artifacts'/path.relative_to(root), root)
        data = {}
        for name in MANIFESTS:
            path=root/name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Missing private provenance manifest')
            data[name]=sha256(path)
        proof=target/'private_artifacts/reports/private/hosted_provenance_sha256.json'
        proof.parent.mkdir(parents=True,exist_ok=True)
        proof.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        (target/'.dockerignore').write_text('.git\n__pycache__\n*.pyc\n.DS_Store\n',encoding='utf-8')
        print('READY: private package prepared at',target)
        print('Contains only six inference/metadata artifacts plus SHA256 manifest attestations.')
        print('DO NOT add this folder to GitHub or share its contents.')
        return target
    except Exception:
        shutil.rmtree(target,ignore_errors=True)
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    prepare(args.root,args.output)
