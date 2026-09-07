import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Expressões regulares para remover blocos de schemas e rotas antigos.
# Nós vamos focar em remover a classe Document e tudo relacionado a documentos do GED antigo.

patterns_to_remove = [
    r'class DocumentCreate\(BaseModel\):.*?class Enrollment\(EnrollmentCreate\):\n    id: str\n    model_config = ConfigDict\(from_attributes=True\)\n\n', # Removemos schemas
    r'class DocumentCreate.*?class DocumentLifecycleInfo.*?:\n    action_required: str.*?\n\n',
    r'@app\.post\("/api/documents".*?return document\n\n',
    r'@app\.post\("/api/documents/\{document_id\}/upload"\).*?return \{"document_id": document_id, "version": DocumentVersion\.model_validate\(version\)\.model_dump\(\)\}\n\n',
    r'@app\.post\("/api/documents/\{document_id\}/xml"\).*?return \{"document_id": document_id, "schema_version": schema\.code, "xml": xml\}\n\n',
    r'@app\.post\("/api/documents/historico/generate".*?return \{"valid": True, "errors": \[\]\}\n\n',
    r'@app\.post\("/api/ged/categories".*?return transition\n\n',
    r'from app\.api_ged_upload import router as upload_router.*?app\.include_router\(storage_router\)\n\n',
    r'@app\.post\("/api/documents/validate-xsd".*?return \{"valid": True, "errors": \[\]\}\n\n',
    r'@app\.get\("/api/ged/documents".*?return html\n\n',
    r'@app\.post\("/api/schema-versions".*?return schema\n\n',
    r'@app\.get\("/api/documents"\).*?query\.offset\(skip\)\.limit\(limit\)\.all\(\)\n\n',
    r'@app\.post\("/api/documents/advanced-search"\).*?return \{.*?\n\n'
]

new_content = content
for pattern in patterns_to_remove:
    new_content = re.sub(pattern, '', new_content, flags=re.DOTALL)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
