from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Any

import networkx as nx

from .conditions import Condition, DefaultCondition
from .errors import InvalidGraphState
from .prompt import read_user_variable
from .types import Identifier, InputT


class Vertex:
    def __init__(self, identifier: Identifier, prompt: str, choices=None):
        assert prompt
        self._identifier = identifier
        self._prompt = prompt

    @property
    def identifier(self) -> Identifier:
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

    # @classmethod
    # def from_dict(cls, data: Dict) -> RootedDirectedGraph:
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
        # TODO Optimize
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


@dataclass
class LinkedData:
    data: Vertex
    prev: Optional[LinkedData] = None
    next: Optional[LinkedData] = None


class BFSIterator:
    def __init__(self, g: RootedDirectedGraph, context: Optional[Dict] = None):
        self._graph = g
        self._context = {} if context is None else context
        self._history: Optional[LinkedData] = None
        self.visited = set()

    def __iter__(self):
        if not self._graph.root:
            raise InvalidGraphState("no root exists")
        self.queue = [self._graph.root]
        return self

    def __next__(self):
        if len(self.queue):
            v = self.queue.pop(0)
            if v.identifier in self.visited:
                self.__next__()
            self.visited.add(v.identifier)
            adj_vertices = self._graph.get_adjacent(v)
            for adj in adj_vertices:
                self.queue.append(adj.vertex)
            return v
        else:
            raise StopIteration

    def _context_supplied(self, identifier: str) -> Optional[Any]:
        # check context
        if identifier in self._context:
            return self._context[identifier]['auto_input'] if 'auto_input' in self._context[identifier] else None
        return None


class PrompterIterator:
    def __init__(self, g: RootedDirectedGraph, input_mapping: Dict[Identifier, InputT], context: Optional[Dict] = None):
        if context is None:
            context = {}
        self._context = context
        self._graph = g
        self._input_mapping = input_mapping

    def __iter__(self):
        if not self._graph.root:
            raise InvalidGraphState("no root exists")
        self.current_vertex = self._graph.root
        self.previous_vertex: Optional[Vertex] = None
        return self

    def __next__(self):
        if self.current_vertex is None:
            raise StopIteration

        if self.previous_vertex is not None:
            # get supplied data from context and find path
            input_data = self._input_mapping[self.previous_vertex.identifier]
            self.current_vertex = find_path(input_data, self._graph.get_adjacent(self.previous_vertex))
            if self.current_vertex is None:
                raise StopIteration

        self.previous_vertex = self.current_vertex
        # self._append_history(self.)
        return Prompter(self.current_vertex, self._context, self._input_mapping)

    def _append_history(self, current):
        if not self._history:
            self._history = LinkedData(current)
        else:
            prev = self._history
            next = LinkedData(current, prev=prev)
            self._history.next = next
            self._history = next


def evaluate(user_input: InputT, condition: Condition) -> bool:
    return condition.evaluate(user_input)


def find_path(value: InputT, vertices: List[RootedDirectedGraph.AdjacentVertex]) -> Optional[Vertex]:
    path_found = False
    go_to = None
    for v in vertices:
        result = evaluate(value, v.condition)
        if result and path_found:
            raise InvalidGraphState("ambiguous paths")
        if result:
            path_found = True
            go_to = v.vertex

    return go_to


@dataclass
class Prompter:
    vertex: Vertex
    context: Dict
    input_mapping: Dict[Identifier, InputT]

    def prompt(self):
        # check context
        context_supplied_val = self._context_supplied(self.vertex.identifier)
        if context_supplied_val is not None:
            gathered_input = context_supplied_val
        else:
            gathered_input = read_user_variable(self.vertex.prompt)
        self.input_mapping[self.vertex.identifier] = gathered_input

    def _context_supplied(self, identifier: Identifier) -> Optional[InputT]:
        # check context
        if identifier in self.context:
            return self.context[identifier]['auto_input'] if 'auto_input' in self.context[identifier] else None
        return None
