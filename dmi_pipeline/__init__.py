"""
DMI Pipeline - Data operations and agentic automation.

This package implements the agents that operate the DMI data pipeline:
- SourceScout: Registry maintenance
- Harvester: Data collection
- Mapper: Category crosswalks
- WeightsBuilder: CE → CPI weights
- Validator (Janus): QA gates
- Synthesizer: Calculator orchestration
- Publisher: Output generation

Agents may automate but must never change numeric values or methodology.
"""

__version__ = "0.1.0"
