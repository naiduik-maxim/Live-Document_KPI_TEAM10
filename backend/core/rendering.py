"""HTML і справжній DOCX з одного знімка шаблону та збережених даних."""

from html import escape
from io import BytesIO

from docx import Document as WordDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


def xml_text(value):
    """Keep XML 1.0 characters without evaluating templates or HTML."""
    return "".join(
        c
        for c in str(value)
        if c in "\t\n\r"
        or 0x20 <= ord(c) <= 0xD7FF
        or 0xE000 <= ord(c) <= 0xFFFD
        or 0x10000 <= ord(c) <= 0x10FFFF
    )


def content_rows(document):
    """Підготувати однакові поля й порядок для обох форматів виводу."""
    return [
        (
            xml_text(f["label"]),
            (
                xml_text(document.data.get(f["name"], ""))
                if document.data.get(f["name"]) is not None
                else ""
            ),
            f["type"],
        )
        for f in document.template_snapshot["schema"]
    ]


def signature_rows(document):
    fields = document.signatories
    manager_name = (
        fields.get("manager_name", "")
        if document.status in ("approved", "completed")
        else ""
    )
    rows = [
        (
            "Керівник",
            ("", "підпис"),
            (manager_name, "власне ім’я та прізвище"),
        ),
        (
            "Виконавець",
            (fields.get("executor_position", ""), "посада"),
            (fields.get("executor_name", ""), "власне ім’я та прізвище"),
        ),
        (
            "Контактний телефон",
            (fields.get("executor_phone", ""), ""),
            ("", ""),
        ),
    ]
    if fields.get("executor_email"):
        rows.append(
            ("Електронна пошта", (fields["executor_email"], ""), ("", ""))
        )
    return rows


def render_html(document):
    """Сформувати розмітку з екрануванням усіх текстових значень."""
    rows = content_rows(document)
    # Шаблон не виконує код; введений HTML залишається текстом.
    parts = [
        "<article>",
        f"<h1>{escape(xml_text(document.title))}</h1>",
        f'<p>{escape(xml_text(document.template_snapshot["name"]))}</p>',
        "<p>"
        f'{escape(xml_text(document.template_snapshot["description"]))}'
        "</p>",
        "<table><tbody>",
    ]
    for label, value, kind in rows:
        if kind != "textarea":
            parts.append(
                f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
            )
    parts.append("</tbody></table>")
    for label, value, kind in rows:
        if kind == "textarea":
            parts.append(f"<h2>{escape(label)}</h2>")
            for line in value.splitlines():
                parts.append(
                    f"<ul><li>{escape(line[2:])}</li></ul>"
                    if line.startswith("- ")
                    else f"<p>{escape(line)}</p>"
                )
    parts.append('<table style="margin-top:2em;width:100%"><tbody>')
    for label, left, right in signature_rows(document):
        parts.append(f'<tr><th style="text-align:left;width:23%">{label}</th>')
        if left[1]:
            for value, caption in (left, right):
                value = escape(xml_text(value)) or "&nbsp;"
                parts.append(
                    '<td style="text-align:center;padding:0 .5em">'
                    f'<div style="border-bottom:1px solid">{value}</div>'
                    f"<small>({caption})</small></td>"
                )
        else:
            parts.append(f'<td colspan="2">{escape(xml_text(left[0]))}</td>')
        parts.append("</tr>")
    parts.append("</tbody></table></article>")
    return "".join(parts)


def render_docx(document):
    """Створити OOXML із заголовками, таблицею та списками на A4."""
    doc = WordDocument()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    doc.add_heading(xml_text(document.title), 0)
    doc.add_paragraph(xml_text(document.template_snapshot["name"]))
    doc.add_paragraph(xml_text(document.template_snapshot["description"]))
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    # Використовуємо той самий знімок і поля, що й у HTML-перегляді.
    rows = content_rows(document)
    for label, value, kind in rows:
        if kind != "textarea":
            cells = table.add_row().cells
            cells[0].text = label
            cells[1].text = value
    for label, value, kind in rows:
        if kind == "textarea":
            doc.add_heading(label, level=1)
            for line in value.splitlines():
                doc.add_paragraph(
                    line[2:] if line.startswith("- ") else line,
                    style="List Bullet" if line.startswith("- ") else None,
                )
    doc.add_paragraph()
    append_signature_table(doc, document)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def append_signature_table(doc, document):
    table = doc.add_table(rows=0, cols=3)
    table.autofit = False
    widths = [Cm(3.8), Cm(5.1), Cm(7.6)]
    for column, width in zip(table.columns, widths):
        column.width = width
    rows = signature_rows(document)
    for index, (label, left, right) in enumerate(rows):
        cells = table.add_row().cells
        for cell, width in zip(cells, widths):
            cell.width = width
        cells[0].text = label
        if left[1]:
            for cell, (value, caption) in zip(cells[1:], (left, right)):
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(xml_text(value) or "\u00a0")
                borders = OxmlElement("w:pBdr")
                line = OxmlElement("w:bottom")
                line.set(qn("w:val"), "single")
                line.set(qn("w:sz"), "4")
                borders.append(line)
                p._p.get_or_add_pPr().append(borders)
                caption_p = cell.add_paragraph()
                caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                caption_p.add_run(f"({caption})").font.size = Pt(8)
        else:
            cells[1].merge(cells[2]).text = xml_text(left[0])
        for cell in table.rows[-1].cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.keep_with_next = index < len(rows) - 1
