import httpx
import logging
from app.database import SessionLocal
from app.models_ged import GEDDocument, ExternalIngestionAudit

logger = logging.getLogger(__name__)

async def notify_erp(document_id: str, new_status: str):
    """
    Background task to notify the ERP about document status changes.
    """
    db = SessionLocal()
    try:
        # Find the document
        doc = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
        if not doc:
            logger.error(f"Webhook error: Document {document_id} not found.")
            return

        # Find the ingestion audit to get the callback URL
        audit = db.query(ExternalIngestionAudit).filter(ExternalIngestionAudit.document_id == document_id).first()
        if not audit or not audit.callback_url:
            logger.info(f"No callback URL found for document {document_id}. Skipping webhook.")
            return

        payload = {
            "document_id": document_id,
            "status": new_status,
            "link": f"/api/documents/{document_id}/rvdd"
        }

        logger.info(f"Triggering webhook to {audit.callback_url} for document {document_id} with status {new_status}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(audit.callback_url, json=payload, timeout=10.0)
                response.raise_for_status()
                logger.info(f"Webhook delivered successfully: {response.status_code}")
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}.")
            except httpx.HTTPStatusError as exc:
                logger.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
    finally:
        db.close()
