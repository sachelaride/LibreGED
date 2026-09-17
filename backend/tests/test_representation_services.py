from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

XSLT = """<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <html><body><h1><xsl:value-of select="document/name"/></h1></body></html>
  </xsl:template>
</xsl:stylesheet>"""
XML = "<document><name>Diploma de Teste</name></document>"


def test_representation_service_versions_and_rendering():
    service_response = client.post(
        "/api/representation-services",
        json={
            "code": "diploma-rvdd",
            "name": "Diploma Digital",
            "document_type": "diploma",
        },
    )
    assert service_response.status_code == 201, service_response.json()
    service_id = service_response.json()["id"]

    version_response = client.post(
        f"/api/representation-services/{service_id}/versions",
        json={"version_label": "v1.05", "xslt_content": XSLT},
    )
    assert version_response.status_code == 201, version_response.json()
    version_id = version_response.json()["id"]
    assert version_response.json()["status"] == "DRAFT"

    publish_response = client.post(
        f"/api/representation-services/{service_id}/versions/{version_id}/publish"
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "PUBLISHED"

    render_response = client.post(
        "/api/representation-services/render",
        json={"service_id": service_id, "xml_content": XML},
    )
    assert render_response.status_code == 200, render_response.json()
    assert render_response.json()["status"] == "SUCCEEDED"
    assert "Diploma de Teste" in render_response.json()["html_content"]


def test_representation_service_rejects_invalid_xslt():
    service_response = client.post(
        "/api/representation-services",
        json={
            "code": "historico-parcial-rv",
            "name": "Histórico Parcial",
            "document_type": "historico_parcial",
        },
    )
    service_id = service_response.json()["id"]
    response = client.post(
        f"/api/representation-services/{service_id}/versions",
        json={"version_label": "v1.00", "xslt_content": "<not-xslt>"},
    )
    assert response.status_code == 422
