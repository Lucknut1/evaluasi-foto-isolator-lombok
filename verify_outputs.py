from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

base = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result\outputs\lapis1_20260912_01a095d1")
xlsx = base / "Hasil_Evaluasi_Lapis_1_Foto_Isolator.xlsx"
html_path = base / "Dashboard_Evaluasi_Lapis_1_Foto_Isolator.html"

with zipfile.ZipFile(xlsx) as archive:
    print("zip_error", archive.testzip())
    root = ET.fromstring(archive.read("xl/workbook.xml"))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    print("sheets", [x.attrib["name"] for x in root.find("m:sheets", ns)])
    detail_xml = archive.read("xl/worksheets/sheet2.xml")
    print("detail_rows", detail_xml.count(b"<x:row"))
    all_xml = b"".join(archive.read(n) for n in archive.namelist() if n.endswith(".xml"))
    print("formula_error_tokens", {x.decode(): all_xml.count(x) for x in [b"#REF!", b"#DIV/0!", b"#VALUE!", b"#NAME?", b"#N/A"]})

html = html_path.read_text(encoding="utf-8")
print("html_rows", html.count('"u":'))
print("html_size", len(html))
print("has_title", "Evaluasi Foto Isolator, Lapis 1" in html)
print("has_filters", 'id="fu"' in html and 'id="fk"' in html and 'id="q"' in html)
