"""Build an installable ZIP containing only the addon folder."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import argparse
import hashlib
import re
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tag', help='Require a release tag matching the TOC version, e.g. v0.3.3')
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
folder = root / 'QuestLite'
version = next(line.split(':', 1)[1].strip() for line in
               (folder / 'QuestLite.toc').read_text().splitlines()
               if line.startswith('## Version:'))
if not re.fullmatch(r'\d+\.\d+\.\d+', version):
    parser.error(f'Invalid TOC version: {version!r}')
if args.tag is not None and args.tag != f'v{version}':
    parser.error(f'Release tag {args.tag!r} must match TOC version v{version}')
for line in (folder / 'QuestLite.toc').read_text().splitlines():
    entry = line.strip()
    if entry and not entry.startswith('#') and not (folder / entry.replace('\\', '/')).is_file():
        parser.error(f'Missing TOC file: {entry}')
output = root / 'dist' / f'QuestLite-{version}.zip'
output.parent.mkdir(exist_ok=True)
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for file in sorted(folder.rglob('*')):
        if file.is_file():
            archive.write(file, file.relative_to(root).as_posix())
with ZipFile(output) as archive:
    assert archive.testzip() is None
    assert 'QuestLite/QuestLite.toc' in archive.namelist()
print(f'{output} ({output.stat().st_size:,} bytes)')
# A fixed asset name gives the README one download URL across releases.
alias = output.with_name('QuestLite.zip')
shutil.copyfile(output, alias)
checksums = output.with_name('SHA256SUMS.txt')
checksums.write_text(''.join(
    f'{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}\n'
    for file in (output, alias)), encoding='utf-8')
print(f'{alias}\n{checksums}')
