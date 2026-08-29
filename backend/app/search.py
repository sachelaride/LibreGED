import os
from typing import Optional, List
from elasticsearch import Elasticsearch


class SearchService:
    """Adapter para Elasticsearch com fallback em memória para testes."""

    def __init__(self):
        self.enabled = os.getenv("ELASTICSEARCH_ENABLED", "false").lower() == "true"
        self.client: Optional[Elasticsearch] = None
        self.memory_index: dict = {}  # Índice em memória para fallback
        
        if self.enabled:
            try:
                es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
                es_port = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
                self.client = Elasticsearch([{"host": es_host, "port": es_port}])
                # Testar conexão
                self.client.info()
                print(f"✓ Elasticsearch conectado em {es_host}:{es_port}")
            except Exception as e:
                print(f"⚠ Elasticsearch não disponível: {e}. Usando índice em memória.")
                self.enabled = False

    def index_document(self, doc_id: str, document_data: dict) -> bool:
        """Indexar documento para busca rápida."""
        try:
            if self.enabled and self.client:
                self.client.index(
                    index="documents",
                    id=doc_id,
                    document={
                        "document_id": document_data.get("id"),
                        "student_name": document_data.get("student_name", ""),
                        "student_cpf": document_data.get("student_cpf", ""),
                        "course_name": document_data.get("course_name", ""),
                        "document_type": document_data.get("document_type", ""),
                        "title": document_data.get("title", ""),
                        "status": document_data.get("status", ""),
                        "institution_id": document_data.get("institution_id", ""),
                        "created_at": document_data.get("created_at"),
                    },
                )
                return True
            else:
                # Fallback: armazenar em memória
                self.memory_index[doc_id] = document_data
                return True
        except Exception as e:
            print(f"Erro ao indexar documento {doc_id}: {e}")
            return False

    def search(
        self,
        query: str = "",
        student_name: Optional[str] = None,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        institution_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """Buscar documentos com filtros avançados."""
        if self.enabled and self.client:
            return self._search_elasticsearch(
                query=query,
                student_name=student_name,
                document_type=document_type,
                status=status,
                institution_id=institution_id,
                limit=limit,
            )
        else:
            return self._search_memory(
                query=query,
                student_name=student_name,
                document_type=document_type,
                status=status,
                institution_id=institution_id,
                limit=limit,
            )

    def _search_elasticsearch(
        self,
        query: str = "",
        student_name: Optional[str] = None,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        institution_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """Buscar usando Elasticsearch."""
        try:
            filters = []
            if student_name:
                filters.append({"match": {"student_name": student_name}})
            if document_type:
                filters.append({"term": {"document_type.keyword": document_type}})
            if status:
                filters.append({"term": {"status.keyword": status}})
            if institution_id:
                filters.append({"term": {"institution_id.keyword": institution_id}})

            body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [{"multi_match": {"query": query, "fields": ["student_name", "title", "course_name"]}}]
                        if query
                        else [{"match_all": {}}],
                        "filter": filters if filters else [{"match_all": {}}],
                    }
                },
            }

            response = self.client.search(index="documents", body=body)
            return [hit["_source"] for hit in response.get("hits", {}).get("hits", [])]
        except Exception as e:
            print(f"Erro na busca Elasticsearch: {e}")
            return []

    def _search_memory(
        self,
        query: str = "",
        student_name: Optional[str] = None,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        institution_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """Buscar usando índice em memória (fallback)."""
        results = []
        for doc in self.memory_index.values():
            # Aplicar filtros
            if student_name and student_name.lower() not in doc.get("student_name", "").lower():
                continue
            if document_type and doc.get("document_type") != document_type:
                continue
            if status and doc.get("status") != status:
                continue
            if institution_id and doc.get("institution_id") != institution_id:
                continue
            if query and (query.lower() not in doc.get("student_name", "").lower() and
                         query.lower() not in doc.get("title", "").lower()):
                continue
            results.append(doc)

        return results[:limit]

    def delete_document(self, doc_id: str) -> bool:
        """Remover documento do índice."""
        try:
            if self.enabled and self.client:
                self.client.delete(index="documents", id=doc_id)
            else:
                self.memory_index.pop(doc_id, None)
            return True
        except Exception as e:
            print(f"Erro ao deletar documento {doc_id}: {e}")
            return False


# Instância global
search_service = SearchService()
