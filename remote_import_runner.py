#!/usr/bin/env python3
"""
remote_import_runner.py

Orquestrador de importação paralela para o banco de dados remoto do Goauct-Platform.
Executa os 4 arquivos CSV divididos de cada entidade (propriedades, leilões, vínculos)
em paralelo via subprocesso, respeitando a sequência relacional obrigatória:
  Propriedades → Leilões → Vínculos/Histórico

Uso:
    python remote_import_runner.py --stage properties
    python remote_import_runner.py --stage auctions
    python remote_import_runner.py --stage history
    python remote_import_runner.py --stage all
"""

import os
import sys
import argparse
import subprocess
import threading
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Raiz do Agent-Extrator (diretório deste arquivo)
CWD = Path(__file__).resolve().parent

# Diretório do backend do Goauct-Platform
BACKEND_DIR = (CWD.parent / "Goauct-Platform" / "backend").resolve()

# Caminho do Python a usar (o mesmo que está rodando este script)
PY = sys.executable

# Número de partes em que os CSVs foram divididos
NUM_PARTS = 4

# Mapeamento stage → (csv_prefix, --type argumento)
STAGE_MAP = {
    "properties": {
        "csv_prefix": "postgres_property_details",
        "type_arg": None,       # sem --type = properties por padrão
        "label": "Propriedades",
    },
    "auctions": {
        "csv_prefix": "postgres_auction_events",
        "type_arg": "auctions",
        "label": "Leilões",
    },
    "history": {
        "csv_prefix": "postgres_property_auction_history",
        "type_arg": "history",
        "label": "Vínculos/Histórico",
    },
}

# Sequência obrigatória para o modo --stage all
ALL_STAGES = ["properties", "auctions", "history"]

_print_lock = threading.Lock()


def safe_print(msg: str):
    """Thread-safe print."""
    with _print_lock:
        print(msg, flush=True)


def build_cmd(csv_prefix: str, part_num: int, type_arg: str | None) -> list:
    """Monta o comando Python para uma parte específica."""
    csv_filename = f"{csv_prefix}_parte{part_num}.csv"
    csv_path = f"data/split_postgres_csvs/{csv_filename}"
    cmd = [PY, "-u", "scripts/remote_db_import.py", csv_path]
    if type_arg:
        cmd += ["--type", type_arg]
    return cmd


def run_part(part_num: int, cmd: list, label: str, results: dict):
    """Executa um subprocesso para uma parte e captura a saída linha a linha."""
    prefix = f"[{label} | Parte {part_num}]"
    safe_print(f"{prefix} Iniciando: {' '.join(cmd[2:])}")  # oculta o path do python
    try:
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.Popen(
            cmd,
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip("\n\r")
            if line:
                safe_print(f"{prefix} {line}")
        proc.wait()
        results[part_num] = proc.returncode
        if proc.returncode == 0:
            safe_print(f"{prefix} ✅ Concluído com sucesso!")
        else:
            safe_print(f"{prefix} ❌ Falhou com código {proc.returncode}")
    except Exception as exc:
        safe_print(f"{prefix} ❌ Erro inesperado: {exc}")
        results[part_num] = 1


def run_stage(stage: str) -> bool:
    """
    Executa as 4 partes de uma etapa em paralelo.
    Retorna True se todas tiveram sucesso, False se alguma falhou.
    """
    config = STAGE_MAP[stage]
    csv_prefix = config["csv_prefix"]
    type_arg   = config["type_arg"]
    label      = config["label"]

    # Validação: verificar se os arquivos existem no destino
    split_dir = BACKEND_DIR / "data" / "split_postgres_csvs"
    if not split_dir.exists():
        print(f"❌ ERRO: Diretório de CSVs não encontrado: {split_dir}")
        print("ℹ️ Execute a Fase 4 (split + envio para plataforma) antes de importar.")
        return False

    missing = []
    for i in range(1, NUM_PARTS + 1):
        fp = split_dir / f"{csv_prefix}_parte{i}.csv"
        if not fp.exists():
            missing.append(fp.name)
    if missing:
        print(f"\n❌ ERRO: {len(missing)} arquivo(s) de {label} não encontrado(s) em:")
        print(f"   {split_dir}")
        for m in missing:
            print(f"   • {m}")
        print("ℹ️ Execute a Fase 4 (split + envio) para gerar os arquivos no destino.")
        return False

    print("=" * 64)
    print(f"🚀 ETAPA: {label.upper()} — {NUM_PARTS} partes em paralelo")
    print(f"📂 Backend: {BACKEND_DIR}")
    print("=" * 64)

    threads = []
    results = {}
    for i in range(1, NUM_PARTS + 1):
        cmd = build_cmd(csv_prefix, i, type_arg)
        t = threading.Thread(
            target=run_part,
            args=(i, cmd, label, results),
            daemon=True,
        )
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Avaliar resultados
    success = all(results.get(i, 1) == 0 for i in range(1, NUM_PARTS + 1))
    print("-" * 64)
    if success:
        print(f"✅ {label}: Todas as {NUM_PARTS} partes importadas com sucesso!")
    else:
        failed = [i for i in range(1, NUM_PARTS + 1) if results.get(i, 1) != 0]
        print(f"❌ {label}: {len(failed)} parte(s) falharam: {failed}")
    print("-" * 64)
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Orquestrador de importação paralela para o Goauct-Platform"
    )
    parser.add_argument(
        "--stage",
        choices=["properties", "auctions", "history", "all"],
        required=True,
        help="Etapa a executar: properties | auctions | history | all (sequência completa)"
    )
    args = parser.parse_args()

    if not BACKEND_DIR.exists():
        print(f"❌ ERRO: Diretório backend não encontrado: {BACKEND_DIR}")
        print("ℹ️ Certifique-se de que o projeto Goauct-Platform está em '../Goauct-Platform'")
        sys.exit(1)

    if args.stage == "all":
        print("=" * 64)
        print("🔄 IMPORTAÇÃO SEQUENCIAL COMPLETA")
        print("   Propriedades → Leilões → Vínculos/Histórico")
        print("=" * 64 + "\n")

        for stage in ALL_STAGES:
            ok = run_stage(stage)
            if not ok:
                label = STAGE_MAP[stage]["label"]
                print(f"\n⛔ IMPORTAÇÃO ABORTADA na etapa '{label}'.")
                print("   Corrija os erros acima antes de prosseguir para a próxima etapa.")
                sys.exit(1)
            print()

        print("=" * 64)
        print("✅ IMPORTAÇÃO COMPLETA: Todas as 3 etapas finalizadas com sucesso!")
        print("=" * 64)
        sys.exit(0)

    else:
        ok = run_stage(args.stage)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
