"""Export Krita storyboard scenes and their existing notes with full-size rendered PNGs."""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape
from zipfile import BadZipFile, ZipFile

from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image as PdfImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


def read_scenes(project):
    with ZipFile(project) as archive:
        files = [f for f in archive.infolist() if f.filename.endswith("/storyboard/index.xml")]
        if len(files) != 1:
            raise ValueError("Expected one Storyboard Docker index in the saved .kra project.")
        if files[0].file_size > 8 * 1024 * 1024:
            raise ValueError("This storyboard index exceeds the 8 MiB limit.")
        root = ElementTree.fromstring(archive.read(files[0]))
    labels = [c.get("name", "") for c in root.findall("{*}StoryboardCommentList/{*}storyboardcomment")]
    scenes = []
    for item in root.findall("{*}StoryboardItemList/{*}storyboarditem"):
        notes = []
        for index, entry in enumerate(item.findall("{*}comment")):
            value = entry.get("content", "")
            if value.strip():
                label = labels[index] if index < len(labels) else ""
                notes.append((label, value))
        scenes.append((int(item.attrib["frame"]), item.get("item-name", ""), notes))
    return scenes


def write_pdf(project, frames, base, first_frame, numbering_start, last_frame, font, output, images_only=False):
    if not base or "/" in base or "\\" in base:
        raise ValueError("Use the base name from Render Animation, without a directory.")
    if first_frame < 0 or numbering_start < 0:
        raise ValueError("First frame and Start numbering at must be nonnegative.")
    if last_frame is not None and last_frame < first_frame:
        raise ValueError("Last frame must be at or after First frame.")
    selected = [s for s in read_scenes(project) if s[0] >= first_frame and
                (last_frame is None or s[0] <= last_frame)]
    if not selected:
        raise ValueError("The selected time range has no storyboard scene starts.")
    if output.exists():
        raise ValueError("The output file already exists. Choose a new filename.")

    font_name = "Helvetica"
    if font and not images_only:
        font_name = "StoryboardText"
        pdfmetrics.registerFont(TTFont(font_name, str(font)))
    title_style = ParagraphStyle("Title", fontName=font_name, fontSize=16, leading=20, spaceAfter=8)
    note_style = ParagraphStyle("Note", fontName=font_name, fontSize=11, leading=15, spaceAfter=4)

    def paragraph(value, style):
        if font:
            glyphs = pdfmetrics.getFont(font_name).face.charToGlyph
            missing = next((c for c in value if not c.isspace() and not glyphs.get(ord(c))), None)
            if missing:
                raise ValueError(f"Selected font has no glyph for U+{ord(missing):04X}.")
        else:
            try:
                value.encode("cp1252")
            except UnicodeEncodeError as error:
                raise ValueError("Supply a TrueType --font that covers the storyboard text.") from error
        return Paragraph(escape(value).replace("\n", "<br/>"), style)

    width, height = landscape(A4)
    def scene_png(frame):
        number = numbering_start + frame - first_frame
        image_path = frames / f"{base}{number:04d}.png"
        if not image_path.is_file():
            raise ValueError(f"Scene at frame {frame} needs {image_path.name}. Check the render range, "
                             "base name and numbering. Export a complete PNG sequence.")
        with Image.open(image_path) as image:
            if image.format != "PNG":
                raise ValueError(f"{image_path.name} is not a PNG.")
            return str(image_path), image.size

    with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as tmp:
        if images_only:
            canvas = Canvas(tmp, pageCompression=1)
            canvas.setTitle("Storyboard")
            for frame, _, _ in selected:
                path, (pixels_w, pixels_h) = scene_png(frame)
                scale = 720 / max(pixels_w, pixels_h)
                page_w, page_h = pixels_w * scale, pixels_h * scale
                canvas.setPageSize((page_w, page_h))
                canvas.drawImage(path, 0, 0, width=page_w, height=page_h, mask="auto")
                canvas.showPage()
            canvas.save()
        else:
            elements = []
            for frame, name, notes in selected:
                path, (pixels_w, pixels_h) = scene_png(frame)
                scale = min((width - 84) / pixels_w, (height * 0.60) / pixels_h)
                picture = PdfImage(path, width=pixels_w * scale, height=pixels_h * scale)
                if elements:
                    elements.append(PageBreak())
                label = f"{name}  |  Frame {frame}" if name else f"Frame {frame}"
                elements.extend([paragraph(label, title_style), picture, Spacer(1, 10)])
                for label, note in notes:
                    elements.append(paragraph(f"{label}: {note}" if label else note, note_style))
            doc = SimpleDocTemplate(tmp, pagesize=(width, height), title=project.stem,
                                    leftMargin=32, rightMargin=32, topMargin=28, bottomMargin=28)
            doc.build(elements)
        tmp.seek(0)
        with output.open("xb") as destination:
            try:
                shutil.copyfileobj(tmp, destination)
            except BaseException:
                destination.close()
                output.unlink(missing_ok=True)
                raise
    return len(selected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Saved .kra with Storyboard Docker scenes.")
    parser.add_argument("frames", type=Path, help="Folder containing the complete rendered PNG sequence.")
    parser.add_argument("output", type=Path, help="Filename for a new PDF.")
    parser.add_argument("--base", required=True, help="Exact render base name before the frame digits.")
    parser.add_argument("--first-frame", type=int, required=True, help="First frame in Render Animation.")
    parser.add_argument("--numbering-start", type=int, required=True, help="Start numbering at in Render Animation.")
    parser.add_argument("--last-frame", type=int, help="Optional last timeline frame to include.")
    parser.add_argument("--font", type=Path, help="TrueType font for scene names and notes outside Western European text.")
    parser.add_argument("--images-only", action="store_true", help="Fill each page with one scene image and omit scene names and comments.")
    args = parser.parse_args()
    try:
        count = write_pdf(args.project, args.frames, args.base, args.first_frame, args.numbering_start,
                          args.last_frame, args.font, args.output, images_only=args.images_only)
    except (ValueError, OSError, BadZipFile, ElementTree.ParseError, KeyError) as error:
        sys.exit(str(error))
    print(f"Exported {count} storyboard scenes to {args.output}")
