#!/usr/bin/env python
"""
Browse the shape-processing graphs of a ``graphs.json.gz`` spec file in a web
browser.

The graphs written by ``create_graph_specs`` are far too large to be drawn as a
single picture (typically 10^5 nodes). This tool therefore starts a small local
web server (Python standard library only) that serves an interactive page:

* a lazily expanded tree of the graph, starting at the input-file nodes,
* a search over node names, expressions, datasets, variables, ... with a node
  type filter,
* a detail panel for the selected node showing the complete spec, the path from
  the input files (with the combined selection and weight expression that
  applies to the node), its direct children, and the number of descendants by
  node type.

Usage
-----
    python -m xyh.scripts.browse_graphs data/output/shapes-2026-09-30/specs/graphs.json.gz

    # or via the wrapper
    bin/browse_graphs data/output/shapes-2026-09-30/specs/graphs.json.gz

When running on a remote machine, forward the port to your laptop and open the
printed URL there::

    ssh -L 8765:localhost:8765 <host>
"""

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict, deque
from functools import cached_property
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import monotonic
from urllib.parse import parse_qs, urlparse

from xyh.core.io import load_json

logger = logging.getLogger(__name__)

HTML_FILE = Path(__file__).with_name("browse_graphs.html")

# Spec fields that are searched (the potentially huge ``files`` is left out).
SEARCH_FIELDS = (
    "name",
    "expression",
    "campaign",
    "channel",
    "category",
    "dataset",
    "process",
    "variation",
    "variable",
    "output_file",
)

# Fields used for the one-line label of a node, by node type.
LABEL_FIELDS = {
    "InputFilesNode": ("dataset", "channel", "campaign"),
    "FilterNode": ("name",),
    "WeightsNode": ("name",),
    "HistogramNode": ("variable", "variation"),
    "SnapshotNode": ("variation", "category"),
}


class GraphIndex:
    """In-memory index over a node-link graph spec."""

    def __init__(self, graph_specs: dict) -> None:
        self.nodes: dict[str, dict] = {n["id"]: n for n in graph_specs["nodes"]}
        self.children: dict[str, list[str]] = defaultdict(list)
        self.parents: dict[str, list[str]] = defaultdict(list)
        for edge in graph_specs["edges"]:
            self.children[edge["source"]].append(edge["target"])
            self.parents[edge["target"]].append(edge["source"])

        self.roots = sorted(
            (i for i in self.nodes if not self.parents[i]), key=self._sort_key
        )
        for kids in self.children.values():
            kids.sort(key=self._sort_key)

        self.search_text = {
            i: "\n".join(
                str(n["spec"][f]) for f in SEARCH_FIELDS if f in n["spec"]
            ).lower()
            for i, n in self.nodes.items()
        }

    def _sort_key(self, node_id: str) -> tuple:
        node = self.nodes[node_id]
        return (node["type"], self.label(node_id), node_id)

    @cached_property
    def type_counts(self) -> dict[str, int]:
        return dict(Counter(n["type"] for n in self.nodes.values()))

    def label(self, node_id: str) -> str:
        node = self.nodes[node_id]
        spec = node["spec"]
        fields = LABEL_FIELDS.get(node["type"], ())
        parts = [str(spec[f]) for f in fields if f in spec]
        return " · ".join(parts) or node_id[:12]

    def summary(self, node_id: str) -> dict:
        node = self.nodes[node_id]
        return {
            "id": node_id,
            "type": node["type"],
            "label": self.label(node_id),
            "n_children": len(self.children[node_id]),
        }

    def ancestors(self, node_id: str) -> list[str]:
        """Path from a root to the node (following the first parent)."""
        path = [node_id]
        while self.parents[path[-1]]:
            path.append(self.parents[path[-1]][0])
        return path[::-1]

    def descendant_counts(self, node_id: str) -> dict[str, int]:
        seen = set()
        queue = deque(self.children[node_id])
        while queue:
            i = queue.popleft()
            if i in seen:
                continue
            seen.add(i)
            queue.extend(self.children[i])
        return dict(Counter(self.nodes[i]["type"] for i in seen))

    def meta(self) -> dict:
        return {
            "n_nodes": len(self.nodes),
            "n_edges": sum(len(c) for c in self.children.values()),
            "types": self.type_counts,
            "roots": [self.summary(i) for i in self.roots],
        }

    def children_page(self, node_id: str, offset: int, limit: int) -> dict:
        kids = self.children[node_id]
        return {
            "total": len(kids),
            "children": [self.summary(i) for i in kids[offset : offset + limit]],
        }

    def detail(self, node_id: str) -> dict:
        path = self.ancestors(node_id)
        chain = [
            {**self.summary(i), "spec": self._chain_spec(i)} for i in path
        ]
        filters = [
            self.nodes[i]["spec"]["expression"]
            for i in path
            if self.nodes[i]["type"] == "FilterNode"
        ]
        weights = [
            self.nodes[i]["spec"]["expression"]
            for i in path
            if self.nodes[i]["type"] == "WeightsNode"
        ]
        return {
            **self.summary(node_id),
            "spec": self.nodes[node_id]["spec"],
            "path": chain,
            "n_parents": len(self.parents[node_id]),
            "selection": " && ".join(f"({e})" for e in filters),
            "weight": " * ".join(f"({e})" for e in weights),
            "descendants": self.descendant_counts(node_id),
        }

    def _chain_spec(self, node_id: str) -> dict:
        """Compact spec for the path display (no file lists)."""
        spec = self.nodes[node_id]["spec"]
        return {k: v for k, v in spec.items() if k != "files"}

    def search(self, query: str, node_type: str | None, limit: int) -> dict:
        terms = query.lower().split()
        hits = []
        n_hits = 0
        for node_id, text in self.search_text.items():
            if node_type and self.nodes[node_id]["type"] != node_type:
                continue
            if all(t in text for t in terms):
                n_hits += 1
                if len(hits) < limit:
                    hits.append(node_id)
        hits.sort(key=self._sort_key)
        return {"total": n_hits, "results": [self.summary(i) for i in hits]}


def make_handler(index: GraphIndex, source: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            logger.debug(format, *args)

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status: int = 200) -> None:
            self._send(
                status, json.dumps(data).encode(), "application/json"
            )

        def do_GET(self) -> None:  # noqa: N802
            url = urlparse(self.path)
            query = parse_qs(url.query)
            parts = [p for p in url.path.split("/") if p]

            def arg(name: str, default: str = "") -> str:
                return query.get(name, [default])[0]

            try:
                if not parts:
                    self._send(
                        200, HTML_FILE.read_bytes(), "text/html; charset=utf-8"
                    )
                elif parts == ["api", "meta"]:
                    self._json({**index.meta(), "source": str(source)})
                elif parts == ["api", "search"]:
                    self._json(
                        index.search(
                            arg("q"),
                            arg("type") or None,
                            min(int(arg("limit", "200")), 1000),
                        )
                    )
                elif len(parts) == 3 and parts[:2] == ["api", "node"]:
                    if parts[2] not in index.nodes:
                        self._json({"error": "unknown node"}, 404)
                    else:
                        self._json(index.detail(parts[2]))
                elif len(parts) == 3 and parts[:2] == ["api", "children"]:
                    if parts[2] not in index.nodes:
                        self._json({"error": "unknown node"}, 404)
                    else:
                        self._json(
                            index.children_page(
                                parts[2],
                                int(arg("offset", "0")),
                                int(arg("limit", "200")),
                            )
                        )
                else:
                    self._json({"error": "not found"}, 404)
            except (ValueError, BrokenPipeError) as exc:
                logger.debug("request failed: %s", exc)
                try:
                    self._json({"error": str(exc)}, 400)
                except BrokenPipeError:
                    pass

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("graph_specs", type=Path, help="graphs.json.gz file")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    t0 = monotonic()
    logger.info("Loading %s ...", args.graph_specs)
    index = GraphIndex(load_json(args.graph_specs))
    logger.info(
        "Indexed %d nodes in %.1f s", len(index.nodes), monotonic() - t0
    )

    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(index, args.graph_specs)
    )
    logger.info("Serving on http://%s:%d  (Ctrl+C to stop)", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
