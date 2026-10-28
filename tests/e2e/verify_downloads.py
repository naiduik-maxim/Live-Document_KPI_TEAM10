"""Check the real downloads after the desktop and mobile E2E run."""

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

downloads = list(
    (Path(__file__).parent / "test-results").rglob("completed.docx")
)
assert (
    len(downloads) == 2
), f"Expected desktop and mobile downloads, got {len(downloads)}"
for path in downloads:
    with ZipFile(path) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
        assert "Виправлений український текст" in "".join(root.itertext())
        assert "<w:tbl" in xml.decode()
        print(
            f"PASS {path.parent.name}: OOXML parses; "
            "saved Ukrainian text and table present"
        )
