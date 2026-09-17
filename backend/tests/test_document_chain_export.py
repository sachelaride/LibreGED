import io
import json
import zipfile

from app import storage
from app.database import SessionLocal
from app.main import app
from app.models import AuditEvent, Institution, User
from app.models_ged import (
    DocumentCategory,
    DocumentTransitionHistory,
    GEDDocument,
    GEDDocumentStatus,
    SignatureLog,
)
from app.models_representation import (
    RepresentationExecution,
    RepresentationService,
    RepresentationServiceVersion,
)
from fastapi.testclient import TestClient

client = TestClient(app)


def test_document_chain_export_includes_manifest_and_related_audit_data():
    with SessionLocal() as db:
        institution = Institution(
            id="inst-chain-export",
            name="IES Teste",
            cnpj="12.345.678/0001-90",
            legal_name="IES Teste Ltda",
        )
        user = User(
            id="user-chain-export",
            username="chain_export_user",
            hashed_password="hash",
            role="admin_global",
            institution_id=institution.id,
        )
        category = DocumentCategory(
            id="cat-chain-export",
            name="Diploma",
            index_code="9001",
        )
        db.add_all([institution, user, category])
        db.commit()

        file_path = storage.STORAGE_ROOT / "chain_export_doc.txt"
        file_path.write_text("conteudo do documento", encoding="utf-8")

        document = GEDDocument(
            id="doc-chain-export",
            title="Diploma Export Test",
            file_path=str(file_path),
            category_id=category.id,
            institution_id=institution.id,
            status=GEDDocumentStatus.VALIDO,
            document_purpose="official",
            is_official=True,
            public_code="public-chain-export",
            extracted_metadata=json.dumps({"tipo": "diploma"}),
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        db.add(
            DocumentTransitionHistory(
                document_id=document.id,
                from_status=GEDDocumentStatus.RASCUNHO,
                to_status=GEDDocumentStatus.VALIDO,
                changed_by_user_id=user.id,
                comments="Validação concluída",
            )
        )
        db.add(
            AuditEvent(
                id="audit-chain-export",
                document_id=document.id,
                entity="document",
                entity_id=document.id,
                action="validated",
                details="Documento validado para exportação",
                user_id=user.id,
                hash_signature="hash-1",
            )
        )
        db.add(
            SignatureLog(
                document_id=document.id,
                user_id=user.id,
                signature_type="XMLDSig",
                original_file_hash="abc123",
                certificate_subject="CN=Teste",
                certificate_issuer="CN=Autoridade",
                status="SUCCESS",
            )
        )
        service = RepresentationService(
            id="svc-chain",
            code="svc-chain",
            name="Exportação de diploma",
            document_type="diploma",
        )
        version = RepresentationServiceVersion(
            id="ver-chain",
            service_id=service.id,
            revision=1,
            version_label="1.0.0",
            status="PUBLISHED",
            xslt_content="<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform'></xsl:stylesheet>",
            content_hash="content-hash",
            created_by_user_id=user.id,
        )
        db.add_all([service, version])
        db.add(
            RepresentationExecution(
                id="rep-chain-export",
                service_id=service.id,
                service_version_id=version.id,
                document_id=document.id,
                input_xml_hash="xmlhash",
                output_hash="outhash",
                status="SUCCEEDED",
                requested_by_user_id=user.id,
            )
        )
        db.commit()

        response = client.get(f"/api/documents/{document.id}/export-chain")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/zip")

        archive = io.BytesIO(response.content)
        assert zipfile.is_zipfile(archive)

        with zipfile.ZipFile(archive, "r") as zipped:
            names = zipped.namelist()
            assert "manifest.json" in names
            assert "timeline/transitions.json" in names
            assert "audit/audit_events.json" in names
            assert "signatures/signature_logs.json" in names
            assert "representations/representation_executions.json" in names

            manifest = json.loads(zipped.read("manifest.json"))
            assert manifest["document_id"] == document.id
            assert manifest["title"] == "Diploma Export Test"

            audit_payload = json.loads(zipped.read("audit/audit_events.json"))
            assert audit_payload[0]["document_id"] == document.id

            signature_payload = json.loads(zipped.read("signatures/signature_logs.json"))
            assert signature_payload[0]["signature_type"] == "XMLDSig"

            representation_payload = json.loads(zipped.read("representations/representation_executions.json"))
            assert representation_payload[0]["document_id"] == document.id

        file_path.unlink(missing_ok=True)
