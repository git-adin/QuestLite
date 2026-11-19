"""Generate a standalone WoW add-on project from the bundled starter files."""

import argparse
from pathlib import Path
import re


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "template"
TOKEN = re.compile(r"@@([A-Z_]+)@@")


def scaffold(destination, values):
    def substitute(text):
        return TOKEN.sub(lambda match: values[match[1]], text)

    files = []
    for source in sorted(TEMPLATE.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(TEMPLATE)
        if source.suffix == ".in":
            relative = relative.with_suffix("")
            contents = substitute(source.read_text(encoding="utf-8")).encode("utf-8")
        else:
            contents = source.read_bytes()
        files.append((Path(substitute(relative.as_posix())), contents))

    destination.mkdir(parents=True)
    for relative, contents in files:
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="add-on folder and TOC name, such as QuestLite")
    parser.add_argument("--destination", type=Path, help="new project directory, defaulting to the add-on name")
    parser.add_argument("--title", help="display name, defaulting to the add-on name")
    parser.add_argument("--interface", default="16001", help="verified TOC interface number, defaulting to 16001")
    parser.add_argument("--client", default="WoW Forever", help="client display name")
    parser.add_argument("--client-folder", default="_forever_", help="client's game installation folder")
    parser.add_argument("--version", default="0.1.0", help="initial major.minor.patch version")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", args.name):
        parser.error("name must start with a letter and use only letters, digits, hyphens, or underscores")
    if not re.fullmatch(r"[1-9][0-9]*", args.interface):
        parser.error("interface must be a positive TOC interface number")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        parser.error("version must have the form major.minor.patch")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.client_folder):
        parser.error("client-folder must be a single game installation folder name")
    title = args.title or args.name
    if any(char in title + args.client for char in "\r\n\0"):
        parser.error("title and client must each fit on a single line")

    destination = (args.destination or Path(args.name)).absolute()
    values = {
        "ADDON_NAME": args.name,
        "ADDON_TITLE": title,
        "CLIENT": args.client,
        "CLIENT_FOLDER": args.client_folder,
        "INTERFACE": args.interface,
        "SLASH_COMMAND": args.name.lower(),
        "SLASH_KEY": args.name.upper().replace("-", "_"),
        "VERSION": args.version,
    }
    try:
        scaffold(destination, values)
    except FileExistsError:
        parser.error(f"destination already exists: {destination}")
    except OSError as error:
        parser.error(str(error))
    print(destination)


if __name__ == "__main__":
    main()
