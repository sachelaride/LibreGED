from typing import List, Optional
from pydantic import BaseModel
from .schemas_diploma import Model as DiplomaPayload
from .schemas_historico import Model as HistoricoPayload
from .schemas_curriculo import Model as CurriculoPayload

class ValidationRequest(BaseModel):
    diploma: Optional[DiplomaPayload] = None
    historico: Optional[HistoricoPayload] = None
    curriculo: Optional[CurriculoPayload] = None

def validate_documents(req: ValidationRequest) -> List[str]:
    errors = []
    dip = req.diploma
    hist = req.historico
    curr = req.curriculo

    # 1. Validação de Identidade (Match CPF)
    if dip and hist:
        try:
            cpf_dip = dip.dadosDiploma.diplomado.cpf
            cpf_hist = hist.documentoHistoricoEscolarFinal.aluno.cpf
            if cpf_dip != cpf_hist:
                errors.append(f"Inconsistência de CPF: Diploma ({cpf_dip}) != Histórico ({cpf_hist})")
        except AttributeError:
            pass
            
    # 2. Validação de Curso e IES
    if dip and hist:
        try:
            cod_curso_dip = dip.dadosDiploma.dadosCurso.codigoCursoEMEC
            cod_curso_hist = hist.documentoHistoricoEscolarFinal.dadosCurso.codigoCursoEMEC
            if cod_curso_dip != cod_curso_hist:
                errors.append(f"Inconsistência de Curso e-MEC: Diploma ({cod_curso_dip}) != Histórico ({cod_curso_hist})")
        except AttributeError:
            pass

    if dip and curr:
        try:
            cod_curso_dip = dip.dadosDiploma.dadosCurso.codigoCursoEMEC
            cod_curso_curr = curr.dadosCurso.codigoCursoEMEC
            if cod_curso_dip != cod_curso_curr:
                errors.append(f"Inconsistência de Curso e-MEC: Diploma ({cod_curso_dip}) != Currículo ({cod_curso_curr})")
        except AttributeError:
            pass

    # 3. Validação de Carga Horária
    if hist and curr:
        try:
            ch_hist = int(
                hist.documentoHistoricoEscolarFinal.historicoEscolar
                .cargaHorariaCursoIntegralizada.horaRelogio
            )
            ch_minima_curr = sum(
                int(crit.cargasHorariasCriterio.cargaHorariaMinima) 
                for crit in curr.criterioIntegralizacaoRotulos
            )
            if ch_hist < ch_minima_curr:
                errors.append(f"Carga horária insuficiente: Histórico ({ch_hist}) < Mínimo do Currículo ({ch_minima_curr})")
        except (AttributeError, ValueError, TypeError):
            pass

    return errors
