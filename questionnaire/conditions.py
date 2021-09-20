from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import Dict, Any, Callable, Optional

from errors import questionnairerror


class Condition(ABC):
    @abstractmethod
    def evaluate(self, input_data: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict) -> Condition:
        pass


class DefaultCondition(Condition):
    KIND = 'default'

    def evaluate(self, input_data: str):
        return True

    def __str__(self):
        return 'TRUE'

    @classmethod
    def from_dict(cls, data: Dict) -> Condition:
        return cls()


class ComparisonCondition(Condition):
    KIND = 'comparison'

    @unique
    class Operator(Enum):
        EQUAL = 0
        NOT_EQUAL = 1
        LESS_THAN = 2
        LESS_THAN_OR_EQUAL = 3
        GREATER_THAN = 4
        GREATER_THAN_OR_EQUAL = 5

        @classmethod
        def _str_repr(cls) -> Dict[str, ComparisonCondition.Operator]:
            return {
                '==': cls.EQUAL,
                '!=': cls.NOT_EQUAL,
                '<': cls.LESS_THAN,
                '<=': cls.LESS_THAN_OR_EQUAL,
                '>': cls.GREATER_THAN,
                '>=': cls.GREATER_THAN_OR_EQUAL
            }

        @classmethod
        def from_str(cls, operator: str) -> ComparisonCondition.Operator:
            if operator not in cls._str_repr():
                raise questionnairerror(f'no such operator for `{operator}` ')
            return cls._str_repr()[operator]

        def __str__(self) -> str:
            inv_repr = {v: k for k, v in self._str_repr().items()}
            return inv_repr[self]

    def __init__(self, op: Operator, compare_to: Any):
        self._op = op
        self._compare_to = compare_to

    def __str__(self):
        return f'$input {self._op} {self._compare_to}'

    @classmethod
    def from_str(cls, operator: str, compare_to) -> ComparisonCondition:
        return cls(ComparisonCondition.Operator.from_str(operator), compare_to)

    @classmethod
    def from_dict(cls, data: Dict) -> ComparisonCondition:
        return cls(ComparisonCondition.Operator.from_str(data['operator']), data['compare_to'])

    def evaluate(self, input_data: str) -> bool:
        if self._op is ComparisonCondition.Operator.EQUAL:
            return input_data == self._compare_to
        if self._op is ComparisonCondition.Operator.NOT_EQUAL:
            return input_data != self._compare_to
        if self._op is ComparisonCondition.Operator.LESS_THAN:
            return input_data < self._compare_to
        if self._op is ComparisonCondition.Operator.LESS_THAN_OR_EQUAL:
            return input_data <= self._compare_to
        if self._op is ComparisonCondition.Operator.GREATER_THAN:
            return input_data > self._compare_to
        if self._op is ComparisonCondition.Operator.GREATER_THAN_OR_EQUAL:
            return input_data >= self._compare_to


class ConditionFactory:
    BUILDER_FNS: Dict[str, Callable[[Dict], Condition]] = {
        DefaultCondition.KIND: DefaultCondition.from_dict,
        ComparisonCondition.KIND: ComparisonCondition.from_dict
    }

    @staticmethod
    def get(kind: str, data: Optional[Dict] = None) -> Condition:
        if kind not in ConditionFactory.BUILDER_FNS:
            raise questionnairerror(f'no builder found for condition kind `{kind}`')

        return ConditionFactory.BUILDER_FNS[kind](data)

    @staticmethod
    def register(condition_kind: str, fn: Callable[[Dict], Condition]):
        ConditionFactory.BUILDER_FNS[condition_kind] = fn
