"""Build an installable ZIP containing only the addon folder."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
folder = root / 'QuestLite'
version = next(line.split(':', 1)[1].strip() for line in
               (folder / 'QuestLite.toc').read_text().splitlines()
               if line.startswith('## Version:'))
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
