import threading
import time
import logging
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models_ged import FilaProcessamento, GEDDocument, GEDDocumentStatus
from app.models import utc_now
from app.search import search_service

logger = logging.getLogger(__name__)

# Controle global da thread
_worker_thread = None
_stop_event = threading.Event()

def _process_fila_loop():
    """
    Loop infinito que roda em background verificando o banco de dados.
    """
    logger.info("Worker da Fila de Processamento iniciado.")
    
    while not _stop_event.is_set():
        db: Session = SessionLocal()
        try:
            # Busca tarefas pendentes (tentativas < 3)
            tarefa = db.query(FilaProcessamento).filter(
                FilaProcessamento.status.in_(["PENDENTE", "INDEX_PENDING"]),
                FilaProcessamento.tentativas < 3
            ).first()
            
            if not tarefa:
                # Nenhuma tarefa pendente, aguarda um pouco
                db.close()
                _stop_event.wait(5.0) # Dorme por 5 segundos ou até ser interrompido
                continue
                
            current_status = tarefa.status
            # Travar a tarefa
            tarefa.status = "PROCESSANDO"
            tarefa.tentativas += 1
            tarefa.updated_at = utc_now()
            db.commit()
            
            logger.info(f"Processando Job ID: {tarefa.job_id} | Documento: {tarefa.documento_id}")
            
            try:
                # ========================================================
                # Aqui entra a lógica pesada: XML -> XSD -> Assinatura -> RVDD
                # Como essa é uma pipeline de background, nós buscaríamos 
                # o documento no GED e processaríamos as engrenagens.
                # ========================================================
                
                doc = db.query(GEDDocument).filter(GEDDocument.id == tarefa.documento_id).first()
                if doc and current_status == "PENDENTE":
                    # Simulação do tempo de processamento pesado
                    time.sleep(2.0) 
                    
                    # Atualiza o status do documento para PROCESSADO (ou algum status similar na maquina de estados)
                    # Exemplo: VALIDANDO -> ASSINANDO -> ARQUIVADO
                    # Aqui apenas marcamos como VALIDO para simulação de sucesso no background.
                    doc.status = GEDDocumentStatus.VALIDO
                    tarefa.status = "INDEX_PENDING"
                    tarefa.index_payload = (doc.extracted_metadata or doc.title)
                    db.commit()

                if doc and tarefa.status == "INDEX_PENDING":
                    indexed = search_service.index_document(
                        db,
                        doc.id,
                        doc.title,
                        tarefa.index_payload or "",
                        "",
                    )
                    if not indexed:
                        raise RuntimeError("Indexador não aceitou o documento.")
                    tarefa.indexed_at = utc_now()
                    tarefa.status = "CONCLUIDO"
                    tarefa.updated_at = utc_now()
                    db.commit()
                elif not doc:
                    raise RuntimeError("Documento da fila não encontrado.")
                
                logger.info(f"Job {tarefa.job_id} concluído com sucesso!")
                
            except Exception as e:
                # Falha durante o processamento
                db.rollback()
                logger.error(f"Erro no Job {tarefa.job_id}: {str(e)}")
                
                # Atualiza erro
                tarefa.erro_mensagem = str(e)
                if tarefa.tentativas >= 3:
                    tarefa.status = "FALHA"
                else:
                    tarefa.status = "PENDENTE" # Tenta de novo na próxima rodada
                tarefa.updated_at = utc_now()
                db.commit()
                
        except Exception as e:
            logger.error(f"Erro crítico no loop do worker: {str(e)}")
            time.sleep(5)
        finally:
            db.close()

def start_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _stop_event.clear()
        _worker_thread = threading.Thread(target=_process_fila_loop, daemon=True)
        _worker_thread.start()
        logger.info("Thread do Worker disparada.")

def stop_worker():
    if _worker_thread and _worker_thread.is_alive():
        logger.info("Solicitando parada do Worker...")
        _stop_event.set()
        _worker_thread.join(timeout=5.0)
        logger.info("Worker parado.")
