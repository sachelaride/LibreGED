# Dicionário de Dados Educacional - Matriz IES (Portaria 315/2018)

class IESAspects:
    TEMPORALIDADE = "ies:temporalidade"
    CONVERSAO_DIGITAL = "ies:conversao_digital"
    RESTRICAO_ACESSO = "ies:restricao_acesso"


class IESProperties:
    # Relacionamentos (substituem FKs)
    ALUNO_ID = "ies:aluno_id"
    MATRICULA_ID = "ies:matricula_id"
    
    # Propriedades Base do Documento Acadêmico
    CODIGO_SERIE = "ies:codigo_serie"          # ex: "125.43"
    NOME_SERIE = "ies:nome_serie"              # ex: "Assentamentos individuais"
    
    # Propriedades de Temporalidade
    EVENTO_INICIAL = "ies:evento_inicial"      # ex: "encerramento_vinculo", "homologacao", "registro_notas"
    PRAZO_CORRENTE = "ies:prazo_corrente"      # em anos ou "enquanto_vinculo"
    PRAZO_INTERMEDIARIO = "ies:prazo_intermediario"
    DESTINACAO = "ies:destinacao"              # "eliminacao" ou "permanente"
    
    # Propriedades de Conversão Digital (Portaria 360 e 613)
    HASH_ORIGINAL = "ies:hash_original"
    METODO_CAPTURA = "ies:metodo_captura"
    RESPONSAVEL_DIGITALIZACAO = "ies:responsavel_digitalizacao"
    DATA_DIGITALIZACAO = "ies:data_digitalizacao"
    
    # Restrição de Acesso
    MOTIVO_RESTRICAO = "ies:motivo_restricao"  # "saude", "disciplinar", "dados_bancarios"

# Tabela Base de Códigos de Temporalidade (Exemplo de Carga)
IES_TEMPORALITY_RULES = {
    "125.43": {
        "serie": "Assentamentos individuais/dossiês dos alunos",
        "evento_inicial": "encerramento_vinculo",
        "prazo_corrente": "enquanto_vinculo",
        "prazo_intermediario": None,
        "destinacao": "permanente", # A tabela diz 100 anos total
        "prazo_total_anos": 100
    },
    "125.41": {
        "serie": "Histórico escolar e integralização curricular",
        "evento_inicial": "encerramento_vinculo",
        "prazo_corrente": "enquanto_vinculo",
        "prazo_intermediario": 5,
        "destinacao": "permanente"
    },
    "125.21": {
        "serie": "Matrícula/registro",
        "evento_inicial": "encerramento_vinculo",
        "prazo_corrente": "enquanto_vinculo",
        "prazo_intermediario": 5,
        "destinacao": "eliminacao"
    }
}
