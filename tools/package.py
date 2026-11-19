"""Build and verify the addon ZIPs and their SHA-256 checksums."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
from posixpath import normpath
import re
from shutil import copyfile
from tempfile import TemporaryDirectory
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile


ADDON_NAME = "QuestLite"
SOURCE_DIR = "QuestLite"
# Archive paths mapped to paths relative to the checkout.
EXTRAS = {
    "README.md": "QuestLite/README.md",
    "LICENSE": "QuestLite/LICENSE",
    "FOREVERDB_LICENSE.txt": "QuestLite/FOREVERDB_LICENSE.txt",
}


def relative_path(value):
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or ":" in str(path) or not path.parts:
        raise ValueError(f"Expected a relative package path: {value}")
    return path


def checked_file(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError(f"Missing or out-of-tree package file: {relative}")
    return path


def add_runtime_file(source, addon_name, path, files):
    path = PurePosixPath(normpath(path))
    absolute = checked_file(source, path)
    name = path.as_posix()
    if name in files:
        return
    files[name] = absolute
    if absolute.suffix.lower() != ".xml":
        return
    for element in ElementTree.parse(absolute).iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in {"Include", "Script"} and element.get("file"):
            entry = element.get("file").replace("\\", "/")
            addon_prefix = f"Interface/AddOns/{addon_name}/"
            if entry.lower().startswith(addon_prefix.lower()):
                child = relative_path(entry[len(addon_prefix):])
            else:
                child = path.parent / relative_path(entry)
            add_runtime_file(source, addon_name, child, files)


def build(repo_root, addon_name, source_dir, extras, tag=None, output_dir=None):
    """Build configured release assets. Extras maps archive path to checkout path."""
    root = Path(repo_root).resolve()
    source = (root / source_dir).resolve()
    if not source.is_relative_to(root):
        raise ValueError(f"Source directory must be inside the checkout: {source_dir}")
    toc_name = f"{addon_name}.toc"
    toc = checked_file(source, toc_name)
    lines = toc.read_text(encoding="utf-8-sig").splitlines()
    versions = [line.partition(":")[2].strip() for line in lines if line.startswith("## Version:")]
    if len(versions) != 1 or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", versions[0]):
        raise ValueError(f"Expected one numeric major.minor.patch version in {toc_name}")
    version = versions[0]
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Release tag {tag!r} must match TOC version v{version}")

    files = {toc_name: toc}
    for line in lines:
        entry = line.strip()
        if entry and not entry.startswith("#"):
            add_runtime_file(source, addon_name, relative_path(entry), files)
    for archive_name, checkout_path in extras.items():
        path = relative_path(archive_name)
        name = path.as_posix()
        if ".." in path.parts or name in files:
            raise ValueError(f"Invalid or duplicate archive path: {archive_name}")
        files[name] = checked_file(root, relative_path(checkout_path))
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("Package paths must be unique on case-insensitive filesystems")

    output = Path(output_dir) if output_dir is not None else root / "dist"
    output.mkdir(parents=True, exist_ok=True)
    versioned = f"{addon_name}-{version}.zip"
    stable = f"{addon_name}.zip"
    checksums = "SHA256SUMS.txt"
    entries = {f"{addon_name}/{name}": file for name, file in files.items()}
    with TemporaryDirectory(dir=output) as temp:
        staging = Path(temp)
        with ZipFile(staging / versioned, "w", ZIP_DEFLATED) as archive:
            for name, file in sorted(entries.items()):
                archive.writestr(name, file.read_bytes())
        with ZipFile(staging / versioned) as archive:
            if archive.testzip() is not None or set(archive.namelist()) != entries.keys():
                raise ValueError("ZIP failed package verification")
        copyfile(staging / versioned, staging / stable)
        digest = hashlib.sha256((staging / versioned).read_bytes()).hexdigest()
        (staging / checksums).write_text(
            f"{digest}  {versioned}\n{digest}  {stable}\n", encoding="utf-8", newline="\n"
        )
        for name in (versioned, stable, checksums):
            (staging / name).replace(output / name)
    return tuple(output / name for name in (versioned, stable, checksums))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Require a release tag matching the TOC version")
    parser.add_argument("--output-dir", type=Path, help="Write assets outside the default dist directory")
    args = parser.parse_args()
    try:
        paths = build(Path(__file__).resolve().parents[1], ADDON_NAME, SOURCE_DIR, EXTRAS,
                      args.tag, args.output_dir)
    except (OSError, ValueError, ElementTree.ParseError) as error:
        parser.error(str(error))
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
