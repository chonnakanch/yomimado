"""Portable saved-data contract; no screenshots, caches or machine-local IDs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import SaveSentenceRequest, SaveWordRequest

MAX_BACKUP_BYTES = 16 * 1024 * 1024
MAX_BACKUP_RECORDS = 50_000


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Backup dates must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError) as error:
        raise ValueError("Invalid backup date") from error


BackupDate = Annotated[str, Field(max_length=64), AfterValidator(_timestamp)]


class BackupWord(SaveWordRequest):
    model_config = ConfigDict(extra="forbid", strict=True)
    createdAt: BackupDate

    @model_validator(mode="after")
    def validate_saved_fields(self):
        for value in (self.surface, self.reading, self.dictionaryForm, self.sourceText):
            if value != value.strip():
                raise ValueError("Saved fields must not have surrounding whitespace")
        if any(not value.strip() or len(value) > 2000 for value in self.meanings):
            raise ValueError("Invalid saved dictionary meaning")
        return self


class BackupSentence(SaveSentenceRequest):
    model_config = ConfigDict(extra="forbid", strict=True)
    createdAt: BackupDate

    @model_validator(mode="after")
    def validate_saved_fields(self):
        if not self.sourceText.strip() or self.sourceText != self.sourceText.strip():
            raise ValueError("Invalid saved sentence")
        if self.translatedText is not None and (
            not self.translatedText.strip() or self.translatedText != self.translatedText.strip()
        ):
            raise ValueError("Invalid saved translation")
        return self


class VocabularyBackup(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    format: Literal["yomimado-saved"] = "yomimado-saved"
    version: Literal[1] = 1
    dictionaryAttribution: Literal[
        "JMdict (EDRDG), CC BY-SA 4.0. "
        "https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project.html"
    ] = (
        "JMdict (EDRDG), CC BY-SA 4.0. "
        "https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project.html"
    )
    createdAt: BackupDate
    words: list[BackupWord] = Field(max_length=MAX_BACKUP_RECORDS)
    sentences: list[BackupSentence] = Field(max_length=MAX_BACKUP_RECORDS)

    @field_validator("version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Invalid backup version")
        return value


class RestoreSummary(BaseModel):
    wordsAdded: int = 0
    wordsSkipped: int = 0
    sentencesAdded: int = 0
    sentencesSkipped: int = 0


def parse_backup(data: bytes) -> VocabularyBackup:
    if len(data) > MAX_BACKUP_BYTES:
        raise ValueError("The backup exceeds the 16 MiB size limit")

    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate backup field")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Invalid JSON number")

    try:
        decoded = json.loads(data, object_pairs_hook=unique_fields, parse_constant=invalid_constant)
        # All envelope fields are required in files, including version/format.
        if not isinstance(decoded, dict) or not {"format", "version"} <= decoded.keys():
            raise ValueError("Missing backup format")
        backup = VocabularyBackup.model_validate(decoded)
        # Reject unpaired UTF-16 surrogates before reaching SQLite's UTF-8 fields.
        backup.model_dump_json().encode("utf-8")
        return backup
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("This is not a supported YomiMado saved-data backup") from error
