from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union

import networkx as nx

from conditions import Condition, DefaultCondition
from errors import InvalidGraphState
from prompt import read_user_variable


class Vertex:
    def __init__(self, identifier: Union[int, str], prompt: str, choices=None):
        assert prompt
        self._identifier = identifier
        self._prompt = prompt

    @property
    def identifier(self) -> Union[int, str]:
        return self._identifier

    @property
    def prompt(self) -> str:
        return self._prompt

    def __hash__(self):
        return hash((self._identifier, self._prompt))

    def __eq__(self, other: Vertex):
        return self._prompt == other.prompt and \
               self._identifier == other.identifier

    def __str__(self):
        return f'{self._prompt}'


class RootedDirectedGraph:
    @dataclass
    class AdjacentVertex:
        vertex: Vertex
        condition: Condition

    #@classmethod
    #def from_dict(cls, data: Dict) -> RootedDirectedGraph:
    #    data = {
    #        0: {
    #            'parent': None,
    #            'prompt': '',
    #            'condition': {
    #                'kind': 'comparison',
    #                'operator': '<',
    #                'compare_to': ''
    #            }
    #        },
    #        1: {
    #            'parent': 0,
    #            'prompt': ''
    #        },
    #        2: {
    #            'parent': 1,
    #            'prompt': ''
    #        }

    #    }

    def __init__(self):
        self._graph = nx.MultiDiGraph()
        self._root = None

    def _check_and_set_root(self, v):
        if self.root and self.root is not v:
            raise InvalidGraphState("graph already has a root")

        self._root = v

    def add_vertex(self, v: Vertex, root=False):
        if root:
            self._check_and_set_root(v)

        self._graph.add_node(v)

    def add_edge(self, source: Vertex, destination: Vertex, condition: Condition, root=False):
        # assert no root already exists
        if root:
            self._check_and_set_root(source)

        # assert no more than 1 edge exist with DefaultEdge
        if isinstance(condition, DefaultCondition):
            if source in self._graph:
                for neighbor, neighbor_dict in self._graph.adj[source].items():
                    for _, e in neighbor_dict.items():
                        if 'condition' in e and isinstance(e['condition'], DefaultCondition):
                            raise InvalidGraphState("vertex already contains a defaulted path")
        self._graph.add_edge(source, destination, condition=condition, label=str(condition))

    @property
    def root(self) -> Optional[Vertex]:
        return self._root

    def is_connected(self) -> bool:
        return nx.is_weakly_connected(self._graph)

    def get_adjacent(self, v: Vertex) -> List[AdjacentVertex]:
        adjacent = []
        if v not in self._graph.adj:
            return adjacent
        for neighbor, neighbor_dict in self._graph.adj[v].items():
            for _, e in neighbor_dict.items():
                adjacent.append(RootedDirectedGraph.AdjacentVertex(neighbor, e['condition']))

        return adjacent


class Evaluator:

    @staticmethod
    def traverse_and_gather(g: RootedDirectedGraph, context=None) -> Dict:
        if context is None:
            context = {}

        if g.root is None:
            raise InvalidGraphState("no root exists")

        current_vertex = g.root
        while current_vertex:
            user_input = read_user_variable(current_vertex.prompt)
            context[current_vertex.prompt] = user_input
            current_vertex = Evaluator.find_path(user_input, g.get_adjacent(current_vertex))

        return context

    @staticmethod
    def find_path(user_input: Any, vertices: List[RootedDirectedGraph.AdjacentVertex]) -> Optional[Vertex]:
        path_found = False
        go_to = None
        for v in vertices:
            result = Evaluator.evaluate(user_input, v.condition)
            if result and path_found:
                raise InvalidGraphState("ambiguous paths")
            if result:
                path_found = True
                go_to = v.vertex

        return go_to

    @staticmethod
    def evaluate(user_input: Any, condition: Condition) -> bool:
        return condition.evaluate(user_input)
