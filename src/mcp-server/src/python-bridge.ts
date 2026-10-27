/**
 * Utilitário compartilhado: invocação do bridge CLI Python.
 * Usa child_process.spawn com stdin pipe para passar o payload JSON.
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Caminho absoluto para o bridge CLI Python. */
export const BRIDGE_PATH = path.resolve(
  __dirname,
  "../../../agents/cli_bridge.py"
);

/** Binário Python a usar (configurável via env var). */
export const PYTHON_BIN = process.env["PYTHON_BIN"] ?? "python3";

/**
 * Invoca o bridge CLI Python via spawn com stdin pipe.
 * Escreve `{ command, payload }` serializado em JSON no stdin e lê a resposta em stdout.
 *
 * @throws Error se o bridge retornar ok=false ou se o processo falhar.
 */
export function invokePythonBridge(
  command: string,
  payload: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const input = JSON.stringify({ command, payload });
    const child = spawn(PYTHON_BIN, [BRIDGE_PATH], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`Bridge Python timeout (15s) para comando '${command}'.`));
    }, 15_000);

    child.on("close", (code) => {
      clearTimeout(timer);
      if (stdout.trim() === "") {
        reject(
          new Error(
            `Bridge Python sem output (exit ${code}). stderr: ${stderr.slice(0, 300)}`
          )
        );
        return;
      }
      try {
        const response = JSON.parse(stdout) as {
          ok: boolean;
          result?: Record<string, unknown>;
          error?: string;
        };
        if (!response.ok) {
          reject(new Error(response.error ?? "Bridge retornou ok=false sem mensagem."));
        } else {
          resolve(response.result ?? {});
        }
      } catch {
        reject(new Error(`Resposta do bridge não é JSON válido: ${stdout.slice(0, 200)}`));
      }
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      reject(new Error(`Falha ao iniciar bridge Python: ${err.message}`));
    });

    child.stdin.write(input);
    child.stdin.end();
  });
}
