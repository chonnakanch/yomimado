import { invoke } from "@tauri-apps/api/core";
import { requestService } from "./service-client";

export interface BackupFile {
  name: string;
  contents: string;
}

export interface RestoreSummary {
  wordsAdded: number;
  wordsSkipped: number;
  sentencesAdded: number;
  sentencesSkipped: number;
}

async function readSummary(response: Response): Promise<RestoreSummary> {
  const result: unknown = await response.json();
  if (!result || typeof result !== "object")
    throw new Error("Backup service returned invalid data");
  const summary = result as Record<string, unknown>;
  for (const key of [
    "wordsAdded",
    "wordsSkipped",
    "sentencesAdded",
    "sentencesSkipped",
  ]) {
    const count = summary[key];
    if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0)
      throw new Error("Backup service returned invalid data");
  }
  return result as RestoreSummary;
}

export async function exportSavedBackup(): Promise<boolean> {
  const response = await requestService("/api/v1/backup", "Backup service");
  const contents = await response.text();
  const saved: unknown = await invoke("save_learning_backup", { contents });
  if (typeof saved !== "boolean")
    throw new Error("Could not confirm the backup was saved");
  return saved;
}

export async function previewSavedBackup(): Promise<{
  file: BackupFile;
  summary: RestoreSummary;
} | null> {
  const file = await invoke<BackupFile | null>("choose_learning_backup");
  if (file === null) return null;
  if (
    !file ||
    typeof file.name !== "string" ||
    typeof file.contents !== "string"
  )
    throw new Error("Could not read the selected backup");
  const response = await requestService(
    "/api/v1/backup/preview",
    "Backup service",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: file.contents,
    },
  );
  return { file, summary: await readSummary(response) };
}

export async function restoreSavedBackup(
  file: BackupFile,
): Promise<RestoreSummary> {
  const response = await requestService(
    "/api/v1/backup/restore",
    "Backup service",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: file.contents,
    },
  );
  return readSummary(response);
}
