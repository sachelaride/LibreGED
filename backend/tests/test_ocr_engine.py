from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.ocr_engine import DocumentAnalyzer


def _create_sample_image(path: Path) -> None:
    image = Image.new("RGB", (1200, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 80), "ALUNO: ANA BEATRIZ  MATRICULA: 2026001", fill="black")
    image.save(path)


def test_ocr_disabled_returns_skipped(tmp_path):
    image_path = tmp_path / "document.png"
    _create_sample_image(image_path)

    result = DocumentAnalyzer().extract_text(str(image_path), preferred_engine="none")

    assert result == {
        "status": "skipped",
        "engine": "none",
        "text": "",
        "reason": "ocr_desabilitado",
    }


def test_rapidocr_extracts_text_from_image(tmp_path):
    pytest.importorskip("rapidocr_onnxruntime")
    image_path = tmp_path / "document.png"
    _create_sample_image(image_path)

    result = DocumentAnalyzer().extract_text(
        str(image_path),
        preferred_engine="rapidocr",
        language="pt",
    )

    assert result["status"] == "success"
    assert result["engine"] == "rapidocr"
    assert "ANA BEATRIZ" in result["text"]
    assert "2026001" in result["text"]


def test_auto_uses_an_available_ocr_engine(tmp_path):
    pytest.importorskip("rapidocr_onnxruntime")
    image_path = tmp_path / "document.png"
    _create_sample_image(image_path)

    result = DocumentAnalyzer().extract_text(str(image_path), preferred_engine="auto")

    assert result["status"] == "success"
    assert result["engine"] == "rapidocr"
    assert "2026001" in result["text"]


def test_rapidocr_extracts_text_from_pdf(tmp_path):
    pytest.importorskip("rapidocr_onnxruntime")
    pytest.importorskip("pymupdf")
    pdf_path = tmp_path / "document.pdf"
    image = Image.new("RGB", (1200, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 80), "ALUNO: ANA BEATRIZ  MATRICULA: 2026001", fill="black")
    image.save(pdf_path, "PDF")

    result = DocumentAnalyzer().extract_text(
        str(pdf_path),
        preferred_engine="rapidocr",
        language="pt",
    )

    assert result["status"] == "success"
    assert result["engine"] == "rapidocr"
    normalized_text = result["text"].replace(" ", "")
    assert "ANABEATRIZ" in normalized_text
    assert "2026001" in result["text"]
