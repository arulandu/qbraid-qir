# Copyright (C) 2023 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
Module defining Cirq LLVM Module elements.

"""

import hashlib
from abc import ABCMeta, abstractmethod
from typing import FrozenSet, List, Optional

import cirq
from pyqir import Context, Module


def generate_module_id(circuit: cirq.Circuit) -> str:
    """
    Generates a QIR module ID from a given Cirq circuit.

    This function serializes the Cirq circuit into a JSON string, computes its SHA-256 hash,
    and converts the hash into an alphanumeric string. The final name is a truncated version,
    prefixed with 'circuit-', to form a concise, semi-unique identifier.

    Args:
        circuit (cirq.Circuit): The Cirq circuit for which a unique name is to be generated.

    Returns:
        str: Alphanumeric module ID for the Cirq circuit

    """
    serialized_circuit = cirq.to_json(circuit)
    hash_object = hashlib.sha256(serialized_circuit.encode())
    hash_hex = hash_object.hexdigest()
    alphanumeric_hash = "".join(filter(str.isalnum, hash_hex))
    truncated_hash = alphanumeric_hash[:7]
    return f"circuit-{truncated_hash}"


class _CircuitElement(metaclass=ABCMeta):
    @classmethod
    def from_element_list(cls, elements):
        return [cls(elem) for elem in elements]

    @abstractmethod
    def accept(self, visitor):
        pass


class _Register(_CircuitElement):
    def __init__(self, register: FrozenSet[cirq.Qid]):
        self._register: register

    def accept(self, visitor):
        visitor.visit_register(self._register)


class _Operation(_CircuitElement):
    def __init__(self, operation: cirq.Operation):
        self._operation = operation

    def accept(self, visitor):
        visitor.visit_operation(self._operation)


class CirqModule:
    def __init__(
        self,
        name: str,
        module: Module,
        num_qubits: int,
        elements: List[_CircuitElement],
    ):
        self._name = name
        self._module = module
        self._elements = elements
        self._num_qubits = num_qubits
        # reg_sizes?

    @property
    def name(self) -> str:
        return self._name

    @property
    def module(self) -> Module:
        return self._module

    @property
    def num_qubits(self) -> int:
        return self._num_qubits

    @classmethod
    def from_circuit(
        cls, circuit: cirq.Circuit, module: Optional[Module] = None
    ) -> "CirqModule":
        """Create a new CirqModule from a cirq.Circuit object."""
        elements: List[_CircuitElement] = []

        # Register(s). Tentatively using cirq.Qid as input. Better approaches might exist tbd.
        elements.append(_Register(circuit.all_qubits()))

        # Operations
        for operation in circuit.all_operations():
            elements.append(_Operation(operation))

        if module is None:
            module = Module(Context(), generate_module_id(circuit))
        return cls(
            name=module.source_filename,
            module=module,
            num_qubits=len(circuit.all_qubits()),
            elements=elements,
        )

    def accept(self, visitor):
        visitor.visit_cirq_module(self)
        for element in self._elements:
            element.accept(visitor)
        visitor.record_output(self)
        visitor.finalize()