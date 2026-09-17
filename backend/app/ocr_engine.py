import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class DocumentAnalyzer:
    """Motor Base de OCR + IA com execução opcional por engine."""

    def __init__(self, ai_provider: str = "gemini"):
        self.ai_provider = ai_provider

    def analyze_document(self, file_path: str, expected_category: str) -> dict:
        """Compatibilidade com o código antigo: retorna dados estruturados em JSON."""
        return self.extract_text(file_path=file_path, preferred_engine="auto", document_type=expected_category)

    def extract_text(
        self,
        file_path: str,
        preferred_engine: str = "auto",
        document_type: str = "documento",
        language: str = "pt",
    ) -> Dict[str, Any]:
        """Extrai texto bruto de arquivos de imagem/PDF usando um motor OCR opcional.

        A implementação é segura por padrão: quando o pacote não está instalado,
        retornamos `status='skipped'` em vez de falhar a operação.
        """
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "engine": preferred_engine, "text": "", "reason": "arquivo_nao_encontrado"}

        engine = self._select_engine(preferred_engine, document_type)
        if engine == "none":
            return {"status": "skipped", "engine": "none", "text": "", "reason": "ocr_desabilitado"}

        if engine == "auto":
            candidates = ["paddleocr", "rapidocr", "tesseract"]
            if document_type.lower() not in {
                "diploma",
                "historico",
                "curriculo",
                "certidao",
                "historico escolar",
                "diploma digital",
            }:
                candidates = ["rapidocr", "tesseract", "paddleocr"]
            for candidate in candidates:
                result = self.extract_text(
                    file_path,
                    preferred_engine=candidate,
                    document_type=document_type,
                    language=language,
                )
                if result.get("status") == "success" and result.get("text"):
                    return result
            return {
                "status": "skipped",
                "engine": "auto",
                "text": "",
                "reason": "nenhum_motor_ocr_disponivel",
            }

        if path.suffix.lower() == ".pdf":
            return self._extract_pdf_text(
                path=path,
                engine=engine,
                document_type=document_type,
                language=language,
            )

        return self._extract_image_text(
            path=path,
            engine=engine,
            document_type=document_type,
            language=language,
        )

    def _extract_pdf_text(
        self,
        path: Path,
        engine: str,
        document_type: str,
        language: str,
    ) -> Dict[str, Any]:
        try:
            import pymupdf
        except Exception:
            return {
                "status": "skipped",
                "engine": engine,
                "text": "",
                "reason": "pdf_rasterizador_nao_instalado",
            }

        try:
            with pymupdf.open(path) as document, tempfile.TemporaryDirectory() as temp_dir:
                pages = []
                for page_number, page in enumerate(document):
                    image_path = Path(temp_dir) / f"page-{page_number + 1}.png"
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                    pixmap.save(image_path)
                    pages.append(
                        self._extract_image_text(
                            path=image_path,
                            engine=engine,
                            document_type=document_type,
                            language=language,
                        )
                    )

            successful_pages = [
                result for result in pages
                if result.get("status") == "success" and result.get("text")
            ]
            if successful_pages:
                return {
                    "status": "success",
                    "engine": successful_pages[0].get("engine", engine),
                    "text": "\n\n".join(result["text"] for result in successful_pages),
                    "reason": "",
                }
            if pages and all(result.get("status") == "skipped" for result in pages):
                return pages[0]
            return {
                "status": "error",
                "engine": engine,
                "text": "",
                "reason": "nenhuma_pagina_processada",
            }
        except Exception as exc:
            return {"status": "error", "engine": engine, "text": "", "reason": str(exc)}

    def _extract_image_text(
        self,
        path: Path,
        engine: str,
        document_type: str,
        language: str,
    ) -> Dict[str, Any]:
        if engine in {"paddleocr", "paddle-ocr"}:
            try:
                from paddleocr import PaddleOCR
            except Exception:
                return {"status": "skipped", "engine": engine, "text": "", "reason": "engine_nao_instalado"}
            ocr = PaddleOCR(lang=language, use_angle_cls=True)
            result = ocr.ocr(str(path), cls=True)
            lines = []
            for page in result or []:
                for item in page or []:
                    if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], (list, tuple)):
                        text = item[1][0] if item[1] else ""
                        if text:
                            lines.append(text)
            text = "\n".join(lines)
            return {"status": "success", "engine": "paddleocr", "text": text, "reason": ""}

        if engine == "tesseract":
            try:
                import pytesseract
                from PIL import Image
            except Exception:
                return {"status": "skipped", "engine": engine, "text": "", "reason": "engine_nao_instalado"}
            try:
                text = pytesseract.image_to_string(Image.open(path), lang=language)
                return {"status": "success", "engine": "tesseract", "text": text.strip(), "reason": ""}
            except Exception as exc:  # pragma: no cover - fallback defensivo
                return {"status": "error", "engine": engine, "text": "", "reason": str(exc)}

        if engine == "rapidocr":
            try:
                from rapidocr_onnxruntime import RapidOCR
            except Exception:
                return {"status": "skipped", "engine": engine, "text": "", "reason": "engine_nao_instalado"}
            try:
                ocr = RapidOCR()
                result, _ = ocr(str(path))
                lines = []
                if result:
                    for item in result:
                        text = item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else ""
                        if text:
                            lines.append(str(text))
                return {"status": "success", "engine": "rapidocr", "text": "\n".join(lines), "reason": ""}
            except Exception as exc:
                return {"status": "error", "engine": engine, "text": "", "reason": str(exc)}

        return {"status": "skipped", "engine": engine, "text": "", "reason": "motor_nao_implementado"}

    def _select_engine(self, preferred_engine: Optional[str], document_type: str) -> str:
        normalized = (preferred_engine or "auto").strip().lower()
        if normalized in {"none", "skip"}:
            return "none"
        if normalized in {"auto", "automatic"}:
            return "auto"
        if normalized in {"paddle", "paddleocr", "paddle-ocr"}:
            return "paddleocr"
        if normalized in {"tesseract", "ocr"}:
            return "tesseract"
        if normalized in {"rapid", "rapidocr"}:
            return "rapidocr"
        return normalized
