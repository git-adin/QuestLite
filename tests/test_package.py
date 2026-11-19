"""Test the release ZIP from the checkout and exercise package validation."""

import hashlib
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ADDON_NAME = "QuestLite"
SOURCE_DIR = "QuestLite"
EXPECTED = {
    "QuestLite.toc", "Core.lua", "QuestVisibility.lua", "Diagnostics.lua",
    "AvailabilityPolicy.lua", "AvailabilityPolicyData.lua", "ForeverDBCorrections.lua",
    "Database.lua", "Options.lua", "DropChances.lua", "Map.lua", "Pins.xml",
    "Minimap.lua", "MinimapButton.lua", "SoftTargetCleanup.lua", "LootSparkles.lua",
    "README.md", "LICENSE", "FOREVERDB_LICENSE.txt",
}

sys.path.insert(0, str(ROOT / "tools"))
from package import build


class PackageTests(unittest.TestCase):
    def test_installable_assets(self):
        toc = ROOT / SOURCE_DIR / f"{ADDON_NAME}.toc"
        version = re.search(r"^## Version:\s*(\S+)", toc.read_text(encoding="utf-8-sig"), re.M)[1]
        with TemporaryDirectory() as temp:
            output = Path(temp) / "out"
            command = [sys.executable, str(ROOT / "tools/package.py"), "--output-dir", str(output)]
            invalid = subprocess.run(command + ["--tag", "invalid"], capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("must match TOC version", invalid.stderr)
            self.assertFalse(output.exists())

            subprocess.run(command + ["--tag", f"v{version}"], check=True, capture_output=True, text=True)
            versioned = output / f"{ADDON_NAME}-{version}.zip"
            stable = output / f"{ADDON_NAME}.zip"
            expected = {f"{ADDON_NAME}/{name}" for name in EXPECTED}
            self.assertEqual(versioned.read_bytes(), stable.read_bytes())
            with ZipFile(stable) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(set(archive.namelist()), expected)
                for entry in expected:
                    source = ROOT / SOURCE_DIR / entry.split("/", 1)[1]
                    self.assertEqual(archive.read(entry), source.read_bytes())
            reported = (output / "SHA256SUMS.txt").read_text().splitlines()
            self.assertEqual(
                reported,
                [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in (versioned, stable)],
            )

    def test_local_xml_dependencies_and_missing_file(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "AddonSource"
            ui = source / "UI"
            ui.mkdir(parents=True)
            (source / "Example.toc").write_text("## Version: 1.0.0\nUI\\Panel.xml\n")
            (ui / "Panel.xml").write_text(
                '<Ui xmlns="http://www.blizzard.com/wow/ui/">'
                '<Include file="Child.xml"/>'
                '<Script file="Interface/AddOns/Example/Core.lua"/>'
                '</Ui>'
            )
            (ui / "Child.xml").write_text('<Ui><Script file="../Core.lua"/></Ui>')
            (source / "DeveloperNotes.md").write_text("Excluded")
            (root / "LICENSE").write_text("Example license")
            (source / "Core.lua").write_text("local addonName = ...")
            output = root / "out"
            _, stable, _ = build(root, "Example", "AddonSource", {"LICENSE": "LICENSE"}, output_dir=output)
            with ZipFile(stable) as archive:
                self.assertEqual(set(archive.namelist()), {
                    "Example/Example.toc", "Example/UI/Panel.xml", "Example/UI/Child.xml",
                    "Example/Core.lua", "Example/LICENSE",
                })
            previous = stable.read_bytes()
            (source / "Core.lua").unlink()
            with self.assertRaisesRegex(ValueError, "Core.lua"):
                build(root, "Example", "AddonSource", {"LICENSE": "LICENSE"}, output_dir=output)
            self.assertEqual(stable.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
