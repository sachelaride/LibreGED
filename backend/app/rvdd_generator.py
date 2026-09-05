from jinja2 import Environment, FileSystemLoader, Template
import qrcode
import base64
from io import BytesIO
from pathlib import Path
import datetime
from sqlalchemy.orm import Session
from app import models_templates

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

def generate_qrcode_base64(data: str) -> str:
    """Gera um QR Code e retorna a string em Base64 para injetar no HTML."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def generate_rvdd_html(document_id: str, document_title: str, db: Session = None, template_id: str = None) -> str:
    """
    Carrega o template rvdd.html ou do banco de dados e injeta as variáveis do Diploma.
    """
    if template_id and db:
        db_template = db.query(models_templates.GEDTemplate).filter_by(id=template_id).first()
        if db_template:
            template = Template(db_template.html_content)
        else:
            template = env.get_template("rvdd.html")
    else:
        template = env.get_template("rvdd.html")
    
    # URL de verificação simulada
    url_validacao = f"https://libreged.edu.br/validar/{document_id}"
    qr_base64 = generate_qrcode_base64(url_validacao)
    
    nome_aluno = "Estudante Demonstração"
    if "João" in document_title:
        nome_aluno = "João da Silva"
        
    html_content = template.render(
        nome_aluno=nome_aluno,
        cpf_aluno="123.456.789-00",
        curso="Sistemas de Informação",
        data_conclusao=datetime.datetime.now().strftime("%d de %B de %Y"),
        qrcode_base64=qr_base64,
        codigo_validacao=document_id.split('-')[0].upper(),
        url_validacao=url_validacao
    )
    
    return html_content
