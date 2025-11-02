#!/usr/bin/env python3
"""Extract flashcards from a PDF with 2x4 grid layout and export to various formats."""

import argparse
import random
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Tuple

import fitz
import genanki


class FlashCardExtractor:
    """Extracts flashcards from a PDF with mirrored 2x4 grid layout."""

    def __init__(self, pdf_path: str) -> None:
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        self.pdf_doc = fitz.open(str(self.pdf_path))

        if len(self.pdf_doc) % 2 != 0:
            print(f"Warning: PDF has {len(self.pdf_doc)} pages. Last page ignored.", file=sys.stderr)

    def _get_rect(self, page: fitz.Page, col: int, row: int) -> fitz.Rect:
        """Get rectangle for cell at (col, row) in 2x4 grid."""
        w, h = page.rect.width / 2, page.rect.height / 4
        return fitz.Rect(col * w, row * h, (col + 1) * w, (row + 1) * h)

    def _extract_pdf(self, page_num: int, col: int, row: int) -> bytes:
        """Extract cell as PDF bytes."""
        page = self.pdf_doc[page_num]
        rect = self._get_rect(page, col, row)

        doc = fitz.open()
        new_page = doc.new_page(width=rect.width, height=rect.height)
        new_page.show_pdf_page(new_page.rect, self.pdf_doc, page_num, clip=rect)

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def _extract_image(self, page_num: int, col: int, row: int, dpi: int = 300) -> bytes:
        """Extract cell as PNG bytes."""
        page = self.pdf_doc[page_num]
        rect = self._get_rect(page, col, row)
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=rect)
        return pix.tobytes("png")

    def _cards(self) -> Iterator[Tuple[int, int, int, int, int]]:
        """Yield (card_num, q_page, a_page, col, row) for each card."""
        card_num = 1
        for pair in range(len(self.pdf_doc) // 2):
            for row in range(4):
                for col in range(2):
                    yield (card_num, pair * 2, pair * 2 + 1, col, row)
                    card_num += 1

    def export_pdf_separate(self, output_dir: str) -> None:
        """Export cards as separate front/back PDFs."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for num, q_page, a_page, col, row in self._cards():
            (out / f"{num:03d}-Front.pdf").write_bytes(self._extract_pdf(q_page, col, row))
            (out / f"{num:03d}-Back.pdf").write_bytes(self._extract_pdf(a_page, 1 - col, row))
            print(f"  Card {num:03d}")

        print(f"✓ Exported to {out}")

    def export_pdf_merged(self, output_dir: str) -> None:
        """Export cards as merged front+back PDFs."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for num, q_page, a_page, col, row in self._cards():
            merged = fitz.open()

            front = fitz.open(stream=self._extract_pdf(q_page, col, row), filetype="pdf")
            merged.insert_pdf(front)
            front.close()

            back = fitz.open(stream=self._extract_pdf(a_page, 1 - col, row), filetype="pdf")
            merged.insert_pdf(back)
            back.close()

            merged.save(str(out / f"{num:03d}-Merged.pdf"))
            merged.close()
            print(f"  Card {num:03d}")

        print(f"✓ Exported to {out}")

    def export_anki(self, output_file: str, deck_name: str = "Imported Flashcards") -> None:
        """Export cards to Anki (.apkg) format."""
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)

        deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), deck_name)
        model = genanki.Model(
            random.randrange(1 << 30, 1 << 31),
            "Image Flashcard",
            fields=[{"name": "Q"}, {"name": "A"}],
            templates=[{
                "name": "Card",
                "qfmt": '<div style="text-align:center">{{Q}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer"><div style="text-align:center">{{A}}</div>',
            }],
            css=".card{text-align:center;background:#fff}img{max-width:100%;height:auto}",
        )

        temp_dir = tempfile.mkdtemp()
        media = []

        try:
            for num, q_page, a_page, col, row in self._cards():
                q_file = f"card_{num:03d}_q.png"
                a_file = f"card_{num:03d}_a.png"

                q_path = Path(temp_dir) / q_file
                q_path.write_bytes(self._extract_image(q_page, col, row))
                media.append(str(q_path))

                a_path = Path(temp_dir) / a_file
                a_path.write_bytes(self._extract_image(a_page, 1 - col, row))
                media.append(str(a_path))

                deck.add_note(genanki.Note(
                    model=model,
                    fields=[f'<img src="{q_file}">', f'<img src="{a_file}">'],
                ))
                print(f"  Card {num:03d}")

            pkg = genanki.Package(deck)
            pkg.media_files = media
            pkg.write_to_file(str(out))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        print(f"✓ Exported to {out}")

    def close(self) -> None:
        self.pdf_doc.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract flashcards from PDF and export to various formats",
        epilog="Example: %(prog)s cards.pdf --export anki -o deck.apkg",
    )
    parser.add_argument("pdf_file", help="Input PDF file")
    parser.add_argument("--export", "-e", required=True, choices=["pdf", "pdf-merged", "anki"])
    parser.add_argument("--output", "-o", help="Output path (default: input basename)")
    parser.add_argument("--deck-name", "-d", default="Imported Flashcards", help="Anki deck name")

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output = args.output
    else:
        output = Path(args.pdf_file).stem + (".apkg" if args.export == "anki" else "")

    try:
        with FlashCardExtractor(args.pdf_file) as ex:
            if args.export == "pdf":
                ex.export_pdf_separate(output)
            elif args.export == "pdf-merged":
                ex.export_pdf_merged(output)
            else:
                ex.export_anki(output, args.deck_name)
    except FileNotFoundError as e:
        sys.exit(f"Error: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
