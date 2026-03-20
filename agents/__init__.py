from .ceo_agent import CEOAgent
from .cpo_agent import CPOAgent
from .cto_agent import CTOAgent
from .cmo_agent import CMOAgent


AGENT_CLASS_MAP = {
    "ceo": CEOAgent,
    "cpo": CPOAgent,
    "cto": CTOAgent,
    "cmo": CMOAgent,
}
