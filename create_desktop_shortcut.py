#!/usr/bin/env python3
"""
create_desktop_shortcut.py

Cria ou atualiza o atalho 'Parcel Auction Dashboard.lnk' na Área de Trabalho (Desktop)
do usuário apontando para 'iniciar_dashboard.bat'.
"""

import os
import sys
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


CWD = Path(__file__).resolve().parent
BAT_PATH = CWD / "iniciar_dashboard.bat"
DESKTOP_DIR = Path(os.path.expanduser("~/Desktop"))
SHORTCUT_PATH = DESKTOP_DIR / "Parcel Auction Dashboard.lnk"
PYTHON_EXE = Path(sys.executable)


def create_shortcut():
    if not BAT_PATH.exists():
        print(f"❌ Erro: {BAT_PATH} não encontrado!")
        sys.exit(1)

    if not DESKTOP_DIR.exists():
        print(f"❌ Erro: Diretório Desktop não encontrado em {DESKTOP_DIR}!")
        sys.exit(1)

    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{SHORTCUT_PATH}')
    $Shortcut.TargetPath = '{BAT_PATH}'
    $Shortcut.WorkingDirectory = '{CWD}'
    $Shortcut.Description = 'Parcel Auction Pipeline Dashboard (http://localhost:5050)'
    $Shortcut.IconLocation = '{PYTHON_EXE},0'
    $Shortcut.Save()
    """

    print("=" * 60)
    print("🖥️  Criando atalho na Área de Trabalho (Desktop)...")
    print(f"🎯 Destino do atalho: {SHORTCUT_PATH}")
    print(f"⚙️  Executável/Script: {BAT_PATH}")
    print(f"📂 Diretório de trabalho: {CWD}")
    print("=" * 60)

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=True
        )
        if SHORTCUT_PATH.exists():
            print(f"✅ Atalho criado com sucesso em:\n   {SHORTCUT_PATH}")
        else:
            print(f"⚠️ Comando executado, mas o arquivo {SHORTCUT_PATH} não foi encontrado.")
    except subprocess.CalledProcessError as err:
        print(f"❌ Erro ao criar atalho: {err.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    create_shortcut()
