"""Kinds of model tasks, used for routing (SPEC §6)."""

from enum import StrEnum


class TaskKind(StrEnum):
    ANSWER = "answer"
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    CLASSIFY_TOPIC = "classify_topic"
    TAG = "tag"
