"""Isolated NumPy generation experiment; not selected by the packaged service.

Only the pinned Manga OCR and Marian policies are supported. Full-prefix decoding
deliberately avoids KV-cache/export complexity until parity is demonstrated.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Policy:
    start: int
    eos: int
    beams: int
    limit: int
    length_penalty: float = 1.0
    early_stopping: bool = False
    no_repeat_ngram: int = 0
    banned: tuple[int, ...] = ()
    forced_eos: bool = False
    renormalize: bool = False


def log_softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))


def generation_scores(
    logits: np.ndarray, ids: np.ndarray, policy: Policy
) -> np.ndarray:
    scores = log_softmax(logits.astype(np.float32))
    scores[:, list(policy.banned)] = -np.inf
    n = policy.no_repeat_ngram
    if n and ids.shape[1] + 1 >= n:
        for row, sequence in enumerate(ids.tolist()):
            prefix = tuple(sequence[-(n - 1) :]) if n > 1 else ()
            blocked = [
                sequence[i + n - 1]
                for i in range(len(sequence) - n + 1)
                if tuple(sequence[i : i + n - 1]) == prefix
            ]
            scores[row, blocked] = -np.inf
    if policy.forced_eos and ids.shape[1] == policy.limit - 1:
        scores.fill(-np.inf)
        scores[:, policy.eos] = 0
    if policy.renormalize:
        scores = log_softmax(scores)
    return scores


def beam_search(step: Callable[[np.ndarray], np.ndarray], policy: Policy) -> list[int]:
    """Batch size one, deterministic beam search with HF-style EOS scoring.

    Hypothesis normalization excludes the decoder prompt and includes the EOS
    score. Candidate ties use stable flattened order; native Torch tie ordering
    is not guaranteed identical and remains a parity risk recorded by the probe.
    """
    if policy.beams < 1 or policy.limit < 2:
        raise ValueError("Invalid generation policy")
    ids = np.full((policy.beams, 1), policy.start, dtype=np.int64)
    beam_scores = np.full(policy.beams, -1e9, dtype=np.float32)
    beam_scores[0] = 0
    completed: list[tuple[float, list[int]]] = []

    def add(score: float, sequence: list[int], generated: int) -> None:
        completed.append((score / generated**policy.length_penalty, sequence))
        completed.sort(key=lambda item: item[0], reverse=True)
        del completed[policy.beams :]

    for _ in range(1, policy.limit):
        scores = generation_scores(step(ids), ids, policy) + beam_scores[:, None]
        width = scores.shape[1]
        flat = scores.ravel()
        candidates = np.argsort(-flat, kind="stable")[: 2 * policy.beams]
        active: list[list[int]] = []
        active_scores: list[float] = []
        for rank, candidate in enumerate(candidates):
            parent, token = divmod(int(candidate), width)
            score = float(flat[candidate])
            if token == policy.eos:
                if rank < policy.beams:
                    add(score, ids[parent].tolist() + [token], ids.shape[1])
            else:
                active.append(ids[parent].tolist() + [token])
                active_scores.append(score)
            if len(active) == policy.beams:
                break
        if len(completed) == policy.beams:
            best_possible = (
                float(flat[candidates[0]]) / ids.shape[1] ** policy.length_penalty
            )
            if policy.early_stopping or completed[-1][0] >= best_possible:
                return completed[0][1]
        if len(active) != policy.beams:
            raise RuntimeError("Generation could not fill its active beams")
        ids = np.asarray(active, dtype=np.int64)
        beam_scores = np.asarray(active_scores, dtype=np.float32)
    for sequence, score in zip(ids.tolist(), beam_scores.tolist()):
        add(score, sequence, len(sequence) - 1)
    return completed[0][1]
