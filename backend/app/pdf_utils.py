import os
import subprocess
import tempfile
import asyncio
import logging
import shutil

logger = logging.getLogger(__name__)

async def convert_html_to_pdf_libreoffice(html_content: str) -> bytes:
    """
    Usa o LibreOffice (soffice) de forma assíncrona para converter HTML para PDF.
    Isso substitui dependências como pdfkit/wkhtmltopdf e permite aderência ao 
    plano sem precisar de Docker.
    """
    # 1. Save HTML to temporary file
    fd, temp_html_path = tempfile.mkstemp(suffix=".html")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    temp_dir = os.path.dirname(temp_html_path)
    output_pdf = temp_html_path.replace(".html", ".pdf")
    
    try:
        # 2. Run LibreOffice Headless
        # Assuming soffice is in PATH. Se não estiver, precisaremos do caminho completo.
        # No Windows, geralmente fica em: C:\Program Files\LibreOffice\program\soffice.exe
        # Vamos tentar 'soffice' que é genérico e, se falhar, usar o path comum do Windows.
        soffice_bin = "soffice"
        if os.name == 'nt' and not shutil.which("soffice"):
            common_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
            if os.path.exists(common_path):
                soffice_bin = common_path

        cmd = [
            soffice_bin,
            "--headless",
            "--convert-to", "pdf:writer_pdf_Export", 
            "--outdir", temp_dir,
            temp_html_path
        ]
        
        # Executa no loop assíncrono para não travar o FastAPI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Erro na conversão LibreOffice: {stderr.decode()}")
            raise Exception("Falha ao converter para PDF")
            
        # 3. Read output PDF
        with open(output_pdf, 'rb') as f:
            pdf_bytes = f.read()
            
        return pdf_bytes
        
    finally:
        # Cleanup
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
        if os.path.exists(output_pdf):
            os.remove(output_pdf)


