"""Persistencia atomica e recuperavel do progresso do jogador."""

from __future__ import annotations

import json
import logging
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)
PHASE_COUNT = 5


class SaveError(OSError):
    """Falha ao persistir o progresso."""


class SaveManager:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else Path(__file__).resolve().parent.parent / "data" / "progress.json"
        )

    @staticmethod
    def default_progress() -> dict[str, Any]:
        return {
            "version": 1,
            "unlocked_levels": [1],
            "completed_levels": [],
            "level_scores": {str(level): 0 for level in range(1, PHASE_COUNT + 1)},
            "best_results": {},
            "last_results": {},
            "total_score": 0,
        }

    def load(self) -> dict[str, Any]:
        try:
            with self.path.open(encoding="utf-8") as file:
                raw_progress = json.load(file)
            progress = self._normalize(raw_progress)
        except FileNotFoundError:
            progress = self.default_progress()
            self._write_or_log(progress)
            return progress
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            LOGGER.warning("Progresso invalido em %s: %s", self.path, error)
            self._preserve_invalid_file()
            progress = self.default_progress()
            self._write_or_log(progress)
            return progress
        except OSError as error:
            LOGGER.error("Nao foi possivel ler o progresso em %s: %s", self.path, error)
            return self.default_progress()

        if progress != raw_progress:
            self._write_or_log(progress)
        return progress

    def save(self, progress: dict[str, Any]) -> None:
        normalized = self._normalize(progress)
        temporary_path: str | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = file.name
                json.dump(normalized, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except OSError as error:
            if temporary_path is not None:
                try:
                    Path(temporary_path).unlink()
                except FileNotFoundError:
                    pass
                except OSError as cleanup_error:
                    LOGGER.warning(
                        "Nao foi possivel remover o arquivo temporario %s: %s",
                        temporary_path,
                        cleanup_error,
                    )
            raise SaveError(f"Nao foi possivel salvar o progresso: {error}") from error

    def record_result(
        self, progress: dict[str, Any], level_number: int, result: dict[str, Any]
    ) -> dict[str, Any]:
        if type(level_number) is not int or not 1 <= level_number <= PHASE_COUNT:
            raise ValueError("Numero de fase invalido no resultado.")
        updated = self._normalize(progress)
        key = str(level_number)
        updated["last_results"][key] = result
        current_best = updated["best_results"].get(key)
        score = result.get("score")
        if type(score) is not int or score < 0:
            raise ValueError("Pontuacao invalida no resultado.")
        if current_best is None or score > current_best["score"]:
            updated["best_results"][key] = result
        updated["level_scores"][key] = max(
            updated["level_scores"][key], score
        )
        updated["total_score"] = sum(updated["level_scores"].values())
        self.save(updated)
        return updated

    def _write_or_log(self, progress: dict[str, Any]) -> None:
        try:
            self.save(progress)
        except SaveError as error:
            LOGGER.error("%s", error)

    def _preserve_invalid_file(self) -> None:
        if not self.path.exists():
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = self.path.with_name(f"{self.path.name}.invalid-{stamp}")
        try:
            os.replace(self.path, backup)
            LOGGER.warning("Arquivo invalido preservado em %s", backup)
        except OSError as error:
            LOGGER.error(
                "Nao foi possivel preservar o arquivo invalido %s: %s",
                self.path,
                error,
            )

    @classmethod
    def _normalize(cls, progress: Any) -> dict[str, Any]:
        if not isinstance(progress, dict):
            raise ValueError("O arquivo de progresso deve conter um objeto JSON.")
        if "version" in progress and progress["version"] != 1:
            raise ValueError("Versao de progresso nao suportada.")

        defaults = cls.default_progress()
        unlocked = progress.get("unlocked_levels", defaults["unlocked_levels"])
        completed = progress.get("completed_levels", defaults["completed_levels"])
        if not isinstance(unlocked, list) or not isinstance(completed, list):
            raise ValueError("Listas de fases do progresso devem ser listas.")
        if any(type(level) is not int or not 1 <= level <= PHASE_COUNT for level in unlocked + completed):
            raise ValueError("O progresso contem identificador de fase invalido.")
        completed_set = set(completed)
        contiguous_completed = 0
        while contiguous_completed + 1 in completed_set:
            contiguous_completed += 1
        completed_set = set(range(1, contiguous_completed + 1))
        highest_unlocked = min(PHASE_COUNT, contiguous_completed + 1)
        unlocked_set = set(range(1, highest_unlocked + 1))

        scores = progress.get("level_scores", {})
        if not isinstance(scores, dict):
            raise ValueError("'level_scores' deve ser um objeto.")
        normalized_scores = defaults["level_scores"].copy()
        for key, value in scores.items():
            if key not in normalized_scores or type(value) is not int or value < 0:
                raise ValueError("Pontuacao por fase invalida.")
            normalized_scores[key] = value

        best_results = cls._normalize_results(progress.get("best_results", {}))
        last_results = cls._normalize_results(progress.get("last_results", {}))
        for key, result in best_results.items():
            normalized_scores[key] = max(normalized_scores[key], result["score"])
        return {
            "version": 1,
            "unlocked_levels": sorted(unlocked_set),
            "completed_levels": sorted(completed_set),
            "level_scores": normalized_scores,
            "best_results": best_results,
            "last_results": last_results,
            "total_score": sum(normalized_scores.values()),
        }

    @staticmethod
    def _normalize_results(results: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(results, dict):
            raise ValueError("Resultados de fase devem formar um objeto.")
        normalized: dict[str, dict[str, Any]] = {}
        list_fields = (
            "essential_items",
            "bonus_items",
            "completed_challenges",
            "completed_objectives",
        )
        for key, result in results.items():
            if key not in {str(level) for level in range(1, PHASE_COUNT + 1)}:
                raise ValueError("Resultado associado a fase desconhecida.")
            if not isinstance(result, dict):
                raise ValueError(f"Resultado invalido para a fase {key}.")
            score = result.get("score")
            movements = result.get("movements", 0)
            elapsed = result.get("elapsed_seconds")
            if type(score) is not int or score < 0:
                raise ValueError(f"Pontuacao invalida no resultado da fase {key}.")
            if type(movements) is not int or movements < 0:
                raise ValueError(f"Deslocamentos invalidos no resultado da fase {key}.")
            if elapsed is not None and (
                type(elapsed) not in (int, float)
                or not math.isfinite(elapsed)
                or elapsed < 0
            ):
                raise ValueError(f"Tempo invalido no resultado da fase {key}.")
            output: dict[str, Any] = {
                "score": score,
                "movements": movements,
                "elapsed_seconds": elapsed,
            }
            for field in list_fields:
                values = result.get(field, [])
                if not isinstance(values, list) or any(
                    not isinstance(value, str) for value in values
                ):
                    raise ValueError(f"Campo {field} invalido no resultado da fase {key}.")
                output[field] = list(dict.fromkeys(values))
            normalized[key] = output
        return normalized
