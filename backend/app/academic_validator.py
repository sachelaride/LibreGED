from typing import Any, List, Optional
from pydantic import BaseModel
from .schemas_diploma import Model as DiplomaPayload
from .schemas_historico import Model as HistoricoPayload
from .schemas_curriculo import Model as CurriculoPayload


class ValidationRequest(BaseModel):
    diploma: Optional[DiplomaPayload] = None
    historico: Optional[HistoricoPayload] = None
    curriculo: Optional[CurriculoPayload] = None


def _safe_get(obj: Any, *attrs: str) -> Any:
    current = obj
    for attr in attrs:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(attr)
        else:
            current = getattr(current, attr, None)
    return current


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_documents(req: ValidationRequest) -> List[str]:
    errors: List[str] = []
    dip = req.diploma
    hist = req.historico
    curr = req.curriculo

    # 1. Validação de Identidade (Match CPF)
    if dip and hist:
        cpf_dip = _safe_get(dip, "dadosDiploma", "diplomado", "cpf")
        cpf_hist = _safe_get(hist, "documentoHistoricoEscolarFinal", "aluno", "cpf")
        if cpf_dip and cpf_hist and cpf_dip != cpf_hist:
            errors.append(f"Inconsistência de CPF: Diploma ({cpf_dip}) != Histórico ({cpf_hist})")

    # 2. Validação de Curso e IES
    if dip and hist:
        cod_curso_dip = _safe_get(dip, "dadosDiploma", "dadosCurso", "codigoCursoEMEC")
        cod_curso_hist = _safe_get(hist, "documentoHistoricoEscolarFinal", "dadosCurso", "codigoCursoEMEC")
        if cod_curso_dip and cod_curso_hist and cod_curso_dip != cod_curso_hist:
            errors.append(f"Inconsistência de Curso e-MEC: Diploma ({cod_curso_dip}) != Histórico ({cod_curso_hist})")

    if dip and curr:
        cod_curso_dip = _safe_get(dip, "dadosDiploma", "dadosCurso", "codigoCursoEMEC")
        cod_curso_curr = _safe_get(curr, "dadosCurso", "codigoCursoEMEC")
        if cod_curso_dip and cod_curso_curr and cod_curso_dip != cod_curso_curr:
            errors.append(f"Inconsistência de Curso e-MEC: Diploma ({cod_curso_dip}) != Currículo ({cod_curso_curr})")

    # 3. Validação de Carga Horária
    if hist and curr:
        ch_hist = _safe_int(
            _safe_get(
                hist,
                "documentoHistoricoEscolarFinal",
                "historicoEscolar",
                "cargaHorariaCursoIntegralizada",
                "horaRelogio",
            )
        )
        criteria = _safe_get(curr, "criterioIntegralizacaoRotulos") or []
        ch_minima_curr = 0
        for crit in criteria:
            crit_value = _safe_get(crit, "cargasHorariasCriterio", "cargaHorariaMinima")
            parsed = _safe_int(crit_value)
            if parsed is not None:
                ch_minima_curr += parsed

        if ch_hist is not None and ch_hist < ch_minima_curr:
            errors.append(f"Carga horária insuficiente: Histórico ({ch_hist}) < Mínimo do Currículo ({ch_minima_curr})")

    return errors
