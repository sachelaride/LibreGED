import os
import sys
import uuid
import hashlib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app import models
from app import models_templates
from app import models_representation
from app import models_workflow
from app import models_ged

def seed_templates_and_services():
    db = SessionLocal()
    try:
        print("Semeando Templates RVDD (HTML)...")
        # Template 1: Diploma Digital Oficial MEC
        rvdd_path = os.path.join(os.path.dirname(__file__), "..", "templates", "rvdd.html")
        with open(rvdd_path, "r", encoding="utf-8") as f:
            rvdd_content = f.read()

        t1 = db.query(models_templates.GEDTemplate).filter_by(name="Modelo Padrão - RVDD Diploma Digital MEC").first()
        if not t1:
            t1 = models_templates.GEDTemplate(
                id=str(uuid.uuid4()),
                name="Modelo Padrão - RVDD Diploma Digital MEC",
                html_content=rvdd_content,
                is_active=True
            )
            db.add(t1)
            print(" [+] Template RVDD Diploma Digital MEC criado.")
        else:
            print(" [=] Template RVDD Diploma Digital MEC já existente.")

        # Template 2: Histórico Escolar RVDD
        t2 = db.query(models_templates.GEDTemplate).filter_by(name="Modelo RVDD - Histórico Escolar de Graduação").first()
        if not t2:
            historico_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Histórico Escolar Digital</title>
    <style>
        body { font-family: 'Outfit', Arial, sans-serif; padding: 40px; color: #1e293b; background: #fff; }
        .header { text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 20px; }
        .header h1 { font-size: 24px; margin: 0; color: #1e3a8a; }
        .header h2 { font-size: 16px; margin: 5px 0 0; color: #64748b; font-weight: normal; }
        .info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 30px 0; padding: 20px; background: #f8fafc; border-radius: 8px; }
        .table-disciplinas { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .table-disciplinas th, .table-disciplinas td { border: 1px solid #cbd5e1; padding: 10px; font-size: 13px; text-align: left; }
        .table-disciplinas th { background: #f1f5f9; color: #334155; }
        .footer { margin-top: 50px; display: flex; justify-content: space-between; font-size: 12px; color: #64748b; }
    </style>
</head>
<body>
    <div class="header">
        <h1>HISTÓRICO ESCOLAR GRADUAÇÃO</h1>
        <h2>Representação Visual do Histórico Escolar Digital (RVDD)</h2>
    </div>
    <div class="info-grid">
        <div><strong>Aluno:</strong> {{ aluno_nome | default('Ana Beatriz Demonstracao') }}</div>
        <div><strong>CPF:</strong> {{ aluno_cpf | default('999.999.999-99') }}</div>
        <div><strong>Matrícula:</strong> {{ matricula | default('2026-PED-001') }}</div>
        <div><strong>Curso:</strong> {{ curso_nome | default('Pedagogia - Licenciatura') }}</div>
    </div>
    <table class="table-disciplinas">
        <thead>
            <tr><th>Código</th><th>Disciplina</th><th>C.H.</th><th>Nota</th><th>Situação</th></tr>
        </thead>
        <tbody>
            <tr><td>PED101</td><td>Fundamentos da Educação</td><td>60h</td><td>9.5</td><td>Aprovado</td></tr>
            <tr><td>PED102</td><td>Psicologia do Desenvolvimento</td><td>60h</td><td>9.0</td><td>Aprovado</td></tr>
            <tr><td>PED103</td><td>Didática Geral e Práticas</td><td>80h</td><td>10.0</td><td>Aprovado</td></tr>
            <tr><td>PED104</td><td>Políticas Públicas em Educação</td><td>60h</td><td>8.5</td><td>Aprovado</td></tr>
        </tbody>
    </table>
    <div class="footer">
        <div>Autenticidade garantida por assinatura ICP-Brasil nos termos do MEC.</div>
        <div>Código de Verificação: {{ codigo_validacao | default('DIP-2026-ABC-XYZ') }}</div>
    </div>
</body>
</html>"""
            t2 = models_templates.GEDTemplate(
                id=str(uuid.uuid4()),
                name="Modelo RVDD - Histórico Escolar de Graduação",
                html_content=historico_html,
                is_active=True
            )
            db.add(t2)
            print(" [+] Template RVDD Histórico Escolar criado.")

        # Template 3: Certificado de Conclusão de Curso
        t3 = db.query(models_templates.GEDTemplate).filter_by(name="Modelo - Certificado Provisório de Conclusão").first()
        if not t3:
            cert_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Certificado de Conclusão</title>
    <style>
        body { font-family: 'Georgia', serif; padding: 60px; text-align: center; color: #0f172a; }
        .border-box { border: 8px double #1e3a8a; padding: 40px; border-radius: 4px; }
        h1 { font-size: 32px; color: #1e3a8a; letter-spacing: 2px; }
        p { font-size: 18px; line-height: 1.8; margin: 30px 0; text-align: justify; }
        .sign { margin-top: 60px; display: inline-block; border-top: 1px solid #334155; padding-top: 8px; width: 300px; }
    </style>
</head>
<body>
    <div class="border-box">
        <h1>CERTIFICADO DE CONCLUSÃO</h1>
        <p>Certificamos para os devidos fins que <strong>{{ aluno_nome | default('Ana Beatriz Demonstracao') }}</strong>, portador(a) do CPF nº <strong>{{ aluno_cpf | default('999.999.999-99') }}</strong>, concluiu com aproveitamento o curso de <strong>{{ curso_nome | default('Pedagogia') }}</strong>, tendo colado grau em sessão solene.</p>
        <div class="sign">Secretaria Geral Acadêmica</div>
    </div>
</body>
</html>"""
            t3 = models_templates.GEDTemplate(
                id=str(uuid.uuid4()),
                name="Modelo - Certificado Provisório de Conclusão",
                html_content=cert_html,
                is_active=True
            )
            db.add(t3)
            print(" [+] Template Certificado Provisório criado.")

        # 2. Serviços de Representação Visual (XML -> RVDD)
        print("Semeando Serviços de Representação Visual...")
        wf_diploma = db.query(models_workflow.Workflow).filter_by(internal_name="emissao-de-diplomas").first()
        wf_id = wf_diploma.id if wf_diploma else None

        s1 = db.query(models_representation.RepresentationService).filter_by(code="diploma-rvdd").first()
        if not s1:
            s1 = models_representation.RepresentationService(
                id=str(uuid.uuid4()),
                code="diploma-rvdd",
                name="Diploma Digital - Representação Visual RVDD",
                document_type="diploma",
                workflow_id=wf_id,
                is_active=True
            )
            db.add(s1)
            db.flush()

            # Versão XSLT publicada
            xslt_sample = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="html" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/">
        <html>
            <head><title>Diploma Digital RVDD</title></head>
            <body>
                <h1>Diploma de Graduação</h1>
                <p>Aluno: <xsl:value-of select="//NomeAluno"/></p>
                <p>Curso: <xsl:value-of select="//NomeCurso"/></p>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>"""
            content_hash = hashlib.sha256(xslt_sample.encode("utf-8")).hexdigest()
            v1 = models_representation.RepresentationServiceVersion(
                id=str(uuid.uuid4()),
                service_id=s1.id,
                revision=1,
                version_label="v1.0",
                status="PUBLISHED",
                xslt_content=xslt_sample,
                content_hash=content_hash,
                published_at=models.utc_now()
            )
            db.add(v1)
            print(" [+] Serviço de Representação 'diploma-rvdd' e Versão v1.0 criados.")

        s2 = db.query(models_representation.RepresentationService).filter_by(code="historico-rvdd").first()
        if not s2:
            s2 = models_representation.RepresentationService(
                id=str(uuid.uuid4()),
                code="historico-rvdd",
                name="Histórico Escolar Digital - Transformação XML",
                document_type="historico_final",
                workflow_id=wf_id,
                is_active=True
            )
            db.add(s2)
            db.flush()

            xslt_hist = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="html" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/">
        <html>
            <head><title>Histórico Digital</title></head>
            <body>
                <h1>Histórico Escolar Final</h1>
                <p>Registro Geral Acadêmico</p>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>"""
            h_hash = hashlib.sha256(xslt_hist.encode("utf-8")).hexdigest()
            v2 = models_representation.RepresentationServiceVersion(
                id=str(uuid.uuid4()),
                service_id=s2.id,
                revision=1,
                version_label="v1.0",
                status="PUBLISHED",
                xslt_content=xslt_hist,
                content_hash=h_hash,
                published_at=models.utc_now()
            )
            db.add(v2)
            print(" [+] Serviço de Representação 'historico-rvdd' e Versão v1.0 criados.")

        db.commit()
        print("Templates e Serviços de Representação semeados com sucesso!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_templates_and_services()
