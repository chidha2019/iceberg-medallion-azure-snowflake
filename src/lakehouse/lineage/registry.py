"""Asset registry: declared lineage metadata for every pipeline step.

Every bronze/silver/gold step is decorated with ``@asset`` which records the
*declared* contract (inputs, output, grain, keys, transformations). The
knowledge-graph crawler reads this registry (``lakehouse export-manifest``)
and cross-checks it against the SQL/implementation it finds in the module —
giving it declared behaviour vs implementation evidence as separate facts.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

Layer = Literal["bronze", "silver", "gold"]


@dataclass(frozen=True)
class Asset:
    name: str                      # e.g. "silver.dim_customer"
    layer: Layer
    output: str                    # fully qualified table
    inputs: tuple[str, ...]        # upstream assets / tables
    grain: str                     # one row per ...
    keys: tuple[str, ...]
    transformations: tuple[str, ...] = ()
    description: str = ""
    owner: str = "data-platform"
    sql_file: str | None = None
    fn: Callable[..., object] | None = field(default=None, compare=False, repr=False)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "layer": self.layer,
            "output": self.output,
            "inputs": list(self.inputs),
            "grain": self.grain,
            "keys": list(self.keys),
            "transformations": list(self.transformations),
            "description": self.description,
            "owner": self.owner,
            "sql_file": self.sql_file,
            "module": self.fn.__module__ if self.fn else None,
            "entry_point": self.fn.__qualname__ if self.fn else None,
        }


class Registry:
    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def register(self, a: Asset) -> None:
        if a.name in self._assets:
            raise ValueError(f"duplicate asset {a.name}")
        self._assets[a.name] = a

    def get(self, name: str) -> Asset:
        return self._assets[name]

    def by_layer(self, layer: Layer) -> list[Asset]:
        return [a for a in self._assets.values() if a.layer == layer]

    def all(self) -> list[Asset]:
        return list(self._assets.values())

    def edges(self) -> list[tuple[str, str]]:
        """(upstream, downstream) pairs — the lineage graph."""
        return [(i, a.name) for a in self._assets.values() for i in a.inputs]

    def topological(self, names: list[str]) -> list[Asset]:
        ordered: list[Asset] = []
        seen: set[str] = set()

        def visit(n: str) -> None:
            if n in seen or n not in self._assets:
                return
            seen.add(n)
            for i in self._assets[n].inputs:
                visit(i)
            ordered.append(self._assets[n])

        for n in names:
            visit(n)
        return ordered


registry = Registry()


def asset(**meta) -> Callable:
    """Decorator registering a pipeline step as a lineage asset."""

    def deco(fn: Callable) -> Callable:
        a = Asset(
            fn=fn,
            inputs=tuple(meta.pop("inputs", ())),
            keys=tuple(meta.pop("keys", ())),
            transformations=tuple(meta.pop("transformations", ())),
            **meta,
        )
        registry.register(a)
        fn.__asset__ = a  # type: ignore[attr-defined]
        return fn

    return deco
