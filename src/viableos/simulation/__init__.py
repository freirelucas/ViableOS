"""VSM multi-agent simulation engine built on Mesa.

Runs a viable system organization as a tick-based simulation with
multi-rate scheduling (Beer's tempo hierarchy), typed VSM communication
channels, and BDI-structured agents.
"""

from viableos.simulation.engine import VSMSimulation
from viableos.simulation.protocols.syntegration import SyntegrationProtocol

__all__ = ["VSMSimulation", "SyntegrationProtocol"]
