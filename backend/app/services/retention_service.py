from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models_ecm import Node, NodeAspect
from app.ecm_dictionary.ies_model import IESAspects, IESProperties, IES_TEMPORALITY_RULES
from sqlalchemy.orm import Session

def apply_temporality_rule(node: Node, codigo_serie: str, db: Session):
    """
    Applies the ECM temporality aspect based on the MEC educational matrix.
    """
    rule = IES_TEMPORALITY_RULES.get(codigo_serie)
    if not rule:
        return # No rule defined
        
    # Ensure the aspect is present
    aspect = db.query(NodeAspect).filter_by(node_id=node.id, aspect_name=IESAspects.TEMPORALIDADE).first()
    if not aspect:
        aspect = NodeAspect(node_id=node.id, aspect_name=IESAspects.TEMPORALIDADE)
        db.add(aspect)
        
    # Set properties
    node.properties[IESProperties.CODIGO_SERIE] = codigo_serie
    node.properties[IESProperties.NOME_SERIE] = rule["serie"]
    node.properties[IESProperties.EVENTO_INICIAL] = rule["evento_inicial"]
    node.properties[IESProperties.PRAZO_CORRENTE] = rule["prazo_corrente"]
    node.properties[IESProperties.PRAZO_INTERMEDIARIO] = rule["prazo_intermediario"]
    node.properties[IESProperties.DESTINACAO] = rule["destinacao"]
    
    # In a full ECM, we would calculate the exact expiration date here 
    # based on the trigger event (e.g., student graduation date).
    # If the event hasn't happened yet, we just store the rules.

def can_be_deleted(node: Node) -> bool:
    """
    Checks if a node can be legally deleted based on its ECM aspects.
    """
    if node.properties.get(IESProperties.DESTINACAO) == "permanente":
        return False
        
    # If there's a legal hold, return False
    if node.properties.get(IESProperties.MOTIVO_RESTRICAO) == "acao_judicial":
        return False
        
    # TODO: Check if the calculated expiration date has passed
    
    return True
