#!/usr/bin/env python3
"""
send_to_platform.py

Copia os arquivos CSV divididos de 'split_postgres_csvs' para o diretório
'backend/data/split_postgres_csvs' do projeto Goauct-Platform.

Possui proteção contra sobrescrita não autorizada:
- Se houver arquivos já existentes no destino com o mesmo nome, requer a flag --overwrite.
- Caso contrário, interrompe com código 1 e alerta orientando a autorização.

Uso:
    python send_to_platform.py [--overwrite] [--target-dir CAMINHO]
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# Suporte a carregamento de .env se python-dotenv estiver disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CWD = Path(__file__).resolve().parent

# Diretório de origem padrão
DEFAULT_SOURCE_DIR = CWD / "split_postgres_csvs"

# Diretório de destino padrão
# Prioridade:
# 1) Variável de ambiente GOAUCT_SPLIT_DIR
# 2) Caminho relativo ../Goauct-Platform/backend/data/split_postgres_csvs
# 3) Fallback absoluto C:/Users/user/Documents/Dev/Projects/Goauct-Platform/backend/data/split_postgres_csvs
ENV_TARGET_DIR = os.getenv("GOAUCT_SPLIT_DIR")
if ENV_TARGET_DIR:
    DEFAULT_TARGET_DIR = Path(ENV_TARGET_DIR).expanduser().resolve()
else:
    rel_target = (CWD.parent / "Goauct-Platform" / "backend" / "data" / "split_postgres_csvs").resolve()
    DEFAULT_TARGET_DIR = rel_target


def get_files_in_dir(directory: Path):
    """Retorna lista de arquivos CSV no diretório."""
    if not directory.exists() or not directory.is_dir():
        return []
    return [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() == ".csv"]


def format_size(bytes_val: int) -> str:
    """Formata tamanho de arquivo em KB ou MB."""
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val / (1024 * 1024):.2f} MB"


def main():
    parser = argparse.ArgumentParser(description="Envio dos CSVs divididos para o Goauct-Platform")
    parser.add_argument(
        "--overwrite", "-f",
        action="store_true",
        help="Autoriza a sobrescrita de arquivos existentes no destino com o mesmo nome"
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=str(DEFAULT_SOURCE_DIR),
        help="Diretório de origem dos CSVs divididos"
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default=str(DEFAULT_TARGET_DIR),
        help="Diretório de destino na plataforma Goauct"
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    target_dir = Path(args.target_dir).resolve()

    print("=" * 60)
    print("🚀 [EXPORTAÇÃO] Envio de CSVs para Goauct-Platform")
    print(f"📂 Origem:  {source_dir}")
    print(f"🎯 Destino: {target_dir}")
    print(f"🔐 Autorização de Sobrescrita: {'HABILITADA' if args.overwrite else 'DESABILITADA'}")
    print("=" * 60)

    # 1. Verificar se pasta de origem existe
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"\n❌ ERRO: O diretório de origem '{source_dir}' não existe!")
        print("ℹ️ Execute primeiro o módulo 'split_csvs.py' para gerar os arquivos divididos.")
        sys.exit(1)

    source_files = get_files_in_dir(source_dir)
    if not source_files:
        print(f"\n❌ ERRO: Nenhum arquivo CSV encontrado em '{source_dir}'!")
        print("ℹ️ Execute primeiro o módulo 'split_csvs.py' para gerar os arquivos.")
        sys.exit(1)

    print(f"\n📦 Arquivos identificados na origem ({len(source_files)}):")
    for sf in source_files:
        print(f"   • {sf.name} ({format_size(sf.stat().st_size)})")

    # 2. Criar diretório de destino se não existir
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"\n❌ ERRO ao criar diretório de destino '{target_dir}': {e}")
        sys.exit(1)

    # 3. Verificar conflitos com arquivos já existentes
    conflicts = []
    for sf in source_files:
        dest_file = target_dir / sf.name
        if dest_file.exists():
            conflicts.append(dest_file)

    if conflicts and not args.overwrite:
        print("\n" + "!" * 60)
        print("⚠️  ATENÇÃO: ARQUIVOS JÁ EXISTEM NO DESTINO!")
        print("!" * 60)
        print(f"Foram encontrados {len(conflicts)} arquivo(s) com o mesmo nome em:")
        print(f"📁 {target_dir}\n")
        for cf in conflicts:
            print(f"   ⚠️ {cf.name} (existente: {format_size(cf.stat().st_size)})")

        print("\n⛔ Sobrescrita NÃO autorizada.")
        print("💡 Para autorizar a substituição desses arquivos:")
        print("   • No Dashboard: marque a opção 'Autorizar sobrescrever arquivos existentes' e clique em Iniciar.")
        print("   • No Terminal: execute com a flag '--overwrite' ou '-f'.")
        print("!" * 60)
        sys.exit(1)

    if conflicts and args.overwrite:
        print(f"\n🔓 Sobrescrita autorizada! {len(conflicts)} arquivo(s) existente(s) serão substituídos.")

    # 4. Copiar arquivos
    print("\nIniciando transferência dos arquivos...")
    copied_count = 0
    total_bytes = 0

    for sf in source_files:
        dest_file = target_dir / sf.name
        is_overwrite = dest_file.exists()
        try:
            shutil.copy2(sf, dest_file)
            size = dest_file.stat().st_size
            total_bytes += size
            action_tag = "SOBRESCRITO" if is_overwrite else "COPIADO"
            print(f"   ✅ [{action_tag}] {sf.name} ({format_size(size)}) -> {dest_file.name}")
            copied_count += 1
        except Exception as err:
            print(f"   ❌ [FALHA] {sf.name}: {err}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print(f"✅ SUCESSO! {copied_count} arquivos enviados com êxito.")
    print(f"📊 Volume total transferido: {format_size(total_bytes)}")
    print(f"🎯 Localização final: {target_dir}")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
