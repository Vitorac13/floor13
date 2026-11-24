"""Servidor web do Floor 13 usando os mesmos módulos Python do jogo original."""
from __future__ import annotations

import json
import secrets
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = Path(__file__).resolve().parent
CUSTOM_LEVELS_PATH = WEB_ROOT / "custom_levels.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms import dijkstra, is_connected  # noqa: E402
from challenge_registry import ChallengeRegistry  # noqa: E402
from graph import Graph  # noqa: E402
from level_manager import LevelManager  # noqa: E402

DISCOVERY = LevelManager.discover_levels(ROOT / "levels")
LEVELS = {level.identifier: level for level in DISCOVERY.levels}
SESSIONS: dict[str, dict[str, Any]] = {}


def json_safe(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (set, frozenset, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value


def level_payload(level) -> dict[str, Any]:
    return {
        "id": level.identifier,
        "number": level.number,
        "name": level.name,
        "vertices": list(level.graph.vertices),
        "edges": [
            [first, second, weight]
            for first in level.graph.vertices
            for second, weight in level.graph.neighbors(first)
            if first < second
        ],
        "start": level.start_floor,
        "exit": level.exit_floor,
        "type": level.challenge_type,
        "items": [
            {
                "id": item.identifier,
                "name": item.name,
                "floor": item.floor,
                "kind": item.kind.name.lower(),
                "key": item.is_key,
            }
            for item in level.items
        ],
        "optional_objectives": [asdict(objective) for objective in level.optional_objectives],
    }


def state_payload(session: dict[str, Any], message: str = "") -> dict[str, Any]:
    level = session["level"]
    state = session["state"]
    current = state.current_floor
    neighbors = [neighbor for neighbor, _ in level.graph.neighbors(current)]
    payload: dict[str, Any] = {
        "session_id": session["id"],
        "level": level_payload(level),
        "current_floor": current,
        "visited_sequence": list(getattr(state, "visited_sequence", [])),
        "visited_floors": list(getattr(state, "visited_floors", [])),
        "valid_destinations": list(getattr(state, "valid_destinations", neighbors)),
        "is_complete": bool(getattr(state, "is_complete", False)),
        "is_blocked": bool(getattr(state, "is_blocked", False)),
        "message": message,
    }
    if hasattr(state, "items_on_current_floor"):
        payload["items_here"] = [
            {"id": item.identifier, "name": item.name, "floor": item.floor, "kind": item.kind.name.lower()}
            for item in state.items_on_current_floor
        ]
        payload["collected"] = list(
            getattr(state, "collected_required", set())
            | getattr(state, "collected_bonus", set())
        )
    else:
        payload["items_here"] = []
        payload["collected"] = []
    if hasattr(state, "progress"):
        payload["challenge_progress"] = list(state.progress)
    if hasattr(state, "total_cost"):
        payload["total_cost"] = state.total_cost
    return payload


def build_custom_level(config: dict[str, Any]):
    challenge = config.get("challenge", {})
    if challenge.get("type") == "euler" and not challenge.get("reference_trail"):
        from euler_challenge import EulerChallengeManager
        raw_graph = config["graph"]
        graph = Graph(raw_graph["vertices"])
        for edge in raw_graph["edges"]:
            graph.add_edge(edge[0], edge[1], edge[2] if len(edge) > 2 else 1)
        trail = EulerChallengeManager.find_eulerian_trail(
            graph, config["start_floor"], config["exit_floor"]
        )
        if trail:
            config = {**config, "challenge": {**challenge, "reference_trail": list(trail)}}
    level = LevelManager.from_config(config)
    LevelManager.validate(level)
    return level


def algorithm_result(level, algorithm: str) -> dict[str, Any]:
    graph = level.graph
    if algorithm == "connect":
        return {"algorithm": "Conectividade", "ok": is_connected(graph), "details": f"{len(graph.vertices)} vértices / {graph.edge_count} arestas"}
    if algorithm == "shortest":
        result = dijkstra(graph, level.start_floor, level.exit_floor)
        return {"algorithm": "Dijkstra / menor custo", "ok": result is not None, "details": None if result is None else {"cost": result[0], "path": result[1]}}
    if algorithm == "hamilton":
        from hamilton_challenge import HamiltonChallengeManager
        challenge = HamiltonChallengeManager.create_for_level(level)
        route = HamiltonChallengeManager.find_hamiltonian_path(challenge)
        return {"algorithm": "Hamiltoniano", "ok": route is not None, "details": " → ".join(map(str, route)) if route else "Nenhuma rota encontrada."}
    if algorithm == "euler":
        from euler_challenge import EulerChallengeManager
        challenge = EulerChallengeManager.create_for_level(level)
        route = EulerChallengeManager.find_eulerian_trail(challenge.graph, challenge.start_floor, challenge.end_floor)
        return {"algorithm": "Euleriano", "ok": route is not None, "details": " → ".join(map(str, route)) if route else "Nenhuma trilha encontrada."}
    raise ValueError("Algoritmo desconhecido.")


class Handler(BaseHTTPRequestHandler):
    server_version = "Floor13Python/1.0"

    def log_message(self, *_args):
        return

    def send_json(self, payload: Any, status: int = 200):
        body = json.dumps(json_safe(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/levels":
            diagnostics = [{"path": str(item.path), "severity": item.severity, "message": item.message} for item in DISCOVERY.diagnostics]
            return self.send_json({"levels": [level_payload(level) for level in LEVELS.values()], "diagnostics": diagnostics})
        if path == "/api/health":
            return self.send_json({"ok": True, "engine": "python", "levels": len(LEVELS)})
        if path.startswith("/api/"):
            return self.send_json({"error": "Rota não encontrada."}, 404)
        relative = path.lstrip("/") or "index.html"
        file_path = (WEB_ROOT / relative).resolve()
        if WEB_ROOT not in file_path.parents and file_path != WEB_ROOT:
            return self.send_error(403)
        if not file_path.is_file():
            return self.send_error(404)
        content_type = "text/html; charset=utf-8" if file_path.suffix == ".html" else "text/css; charset=utf-8" if file_path.suffix == ".css" else "application/javascript; charset=utf-8"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.body()
            if path == "/api/game/start":
                level = LEVELS[data["level_id"]]
                session_id = secrets.token_urlsafe(18)
                session = {"id": session_id, "level": level, "state": ChallengeRegistry.create_state(level)}
                SESSIONS[session_id] = session
                return self.send_json(state_payload(session, "Missão iniciada no motor Python."))
            if path in {"/api/game/move", "/api/game/collect", "/api/game/reset"}:
                session = SESSIONS[data["session_id"]]
                state = session["state"]
                if path.endswith("/move"):
                    message = state.move_to(int(data["destination"]))
                elif path.endswith("/collect"):
                    collected = state.collect_items_here() if hasattr(state, "collect_items_here") else ()
                    message = f"{len(collected)} item(ns) coletado(s)."
                else:
                    state.reset()
                    message = "Fase reiniciada."
                return self.send_json(state_payload(session, message))
            if path == "/api/algorithm":
                level = LEVELS[data["level_id"]]
                return self.send_json(algorithm_result(level, data["algorithm"]))
            if path == "/api/level/validate":
                level = build_custom_level(data["config"])
                return self.send_json({"ok": True, "level": level_payload(level), "message": "Fase válida segundo o LevelManager Python."})
            if path == "/api/level/save":
                config = data["config"]
                level = build_custom_level(config)
                saved = []
                if CUSTOM_LEVELS_PATH.exists():
                    saved = json.loads(CUSTOM_LEVELS_PATH.read_text(encoding="utf-8"))
                saved = [item for item in saved if item.get("id") != config.get("id")]
                saved.append(config)
                CUSTOM_LEVELS_PATH.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
                LEVELS[level.identifier] = level
                return self.send_json({"ok": True, "level": level_payload(level), "message": "Fase salva no catálogo Python."})
            return self.send_json({"error": "Rota não encontrada."}, 404)
        except (KeyError, ValueError, TypeError) as error:
            return self.send_json({"error": str(error)}, 400)
        except Exception as error:  # mantém o erro legível no frontend durante desenvolvimento
            return self.send_json({"error": f"Erro interno do motor Python: {error}"}, 500)


def main():
    if CUSTOM_LEVELS_PATH.exists():
        try:
            for config in json.loads(CUSTOM_LEVELS_PATH.read_text(encoding="utf-8")):
                level = build_custom_level(config)
                LEVELS[level.identifier] = level
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            print(f"Aviso: fases customizadas não carregadas: {error}")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4173
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Floor 13 web em http://127.0.0.1:{port}")
    print(f"Fases Python carregadas: {len(LEVELS)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
