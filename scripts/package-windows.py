"""Package the tested executable and validate release inputs without shell interpolation."""
import hashlib
import os
from pathlib import Path
import re
import zipfile

root = Path(__file__).resolve().parent.parent
source = root / 'tools' / 'hubspot-lotes'
version = re.search(r'^VERSION = "([0-9]+\.[0-9]+\.[0-9]+)"', (source / 'engine.py').read_text(encoding='utf-8'), re.M).group(1)
tag = os.environ.get('RELEASE_TAG', '')
if tag and tag != f'hubspot-lotes-v{version}':
    raise SystemExit(f'Release tag must match engine.VERSION: hubspot-lotes-v{version}')
folder = root / 'dist' / 'windows'
exe = folder / 'HubSpotLotes.exe'
if not exe.is_file():
    raise SystemExit('Tested executable missing')
archive = folder / 'HubSpotLotes-Cliente-Windows.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
    package.write(exe, exe.name)
    package.write(source / 'README.md', 'LEIA-ME.md')
(folder / 'SHA256SUMS.txt').write_text(''.join(f'{hashlib.file_digest(path.open("rb"), "sha256").hexdigest()}  {path.name}\n' for path in [exe, archive]), encoding='utf-8')
(folder / 'release-notes.md').write_text(f'HubSpot Lotes {version} para Windows x64.\n\nBaixe e extraia HubSpotLotes-Cliente-Windows.zip, ou execute HubSpotLotes.exe. Python não precisa ser instalado. Modos em tela requerem Edge/Chrome.\n\nCompilado pelo GitHub Actions após testes locais de formulário e verificação do executável. SHA256SUMS.txt permite conferir a integridade.\n', encoding='utf-8')
print(f'Windows package ready: {version}')
