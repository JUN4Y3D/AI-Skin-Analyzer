"""Finish patch installation in the existing checkout. Run only after reviewing the patch."""
from pathlib import Path
from subprocess import run
import sys
root=Path(__file__).resolve().parents[1]
run([sys.executable,str(root/"scripts/apply_hosted_patch.py")],check=True)
ignore=root/".gitignore"
addition=(root/".gitignore.add").read_text(encoding="utf-8")
text=ignore.read_text(encoding="utf-8")
if "/web/public/" not in text:
    ignore.write_text(text.rstrip()+"\n\n"+addition,encoding="utf-8")
(root/".gitignore.add").unlink()
readme=root/"README.md"
readme_text=readme.read_text(encoding="utf-8")
if "docs/HOSTED_DEPLOYMENT.md" not in readme_text:
    readme.write_text(readme_text.rstrip()+"\n\n## Hosted deployment (optional)\n\nA public Vercel frontend with a separate private-model Railway inference service is documented in [Hosted deployment](docs/HOSTED_DEPLOYMENT.md). This mode sends photos to a remote server and has different privacy implications than the localhost application; it requires securely provisioning privately held model weights. The public source repository does not include model artifacts.\n",encoding="utf-8")
run([sys.executable,str(root/"scripts/build_hosted_frontend.py")],check=True)
print("Host patch installed. Review git diff; do not git add .")
