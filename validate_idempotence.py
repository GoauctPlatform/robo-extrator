#!/usr/bin/env python3
"""
Script de Validação de Idempotência para generate_postgres_csvs.py

Uso: python3 validate_idempotence.py
"""

import os
import sys
import subprocess
import hashlib
import tempfile
import shutil
from datetime import datetime
import pandas as pd
from pathlib import Path

class IdempotenceValidator:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = tempfile.mkdtemp()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "success": True
        }
    
    def log(self, level, message):
        """Log com cor"""
        colors = {
            "info": "\033[94m",    # Blue
            "success": "\033[92m", # Green
            "warning": "\033[93m", # Yellow
            "error": "\033[91m",   # Red
            "reset": "\033[0m"
        }
        prefix = level.upper()
        color = colors.get(level, "")
        reset = colors["reset"]
        print(f"{color}[{prefix}]{reset} {message}")
    
    def hash_csv(self, filepath, ignore_cols=None):
        """Calcula hash de CSV ignorando colunas específicas"""
        if ignore_cols is None:
            ignore_cols = []
        
        df = pd.read_csv(filepath, dtype=str)
        cols_to_keep = [c for c in df.columns if c not in ignore_cols]
        df_copy = df[cols_to_keep].copy()
        csv_str = df_copy.to_csv(index=False)
        return hashlib.md5(csv_str.encode()).hexdigest()
    
    def run_generator(self, label):
        """Executa generate_postgres_csvs.py"""
        self.log("info", f"Executando generate_postgres_csvs.py ({label})...")
        result = subprocess.run(
            ["python3", os.path.join(self.base_dir, "generate_postgres_csvs.py")],
            cwd=self.base_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            self.log("error", f"Execução falhou: {result.stderr}")
            return False
        
        self.log("success", f"Execução completada ({label})")
        return True
    
    def backup_current_files(self, version):
        """Salva arquivos atuais como 'version'"""
        files = [
            "postgres_property_details.csv",
            "postgres_auction_events.csv",
            "postgres_property_auction_history.csv"
        ]
        
        for f in files:
            src = os.path.join(self.base_dir, f)
            dst = os.path.join(self.temp_dir, f"{version}_{f}")
            if os.path.exists(src):
                shutil.copy(src, dst)
                self.log("info", f"Backup: {f} → {version}_{f}")
    
    def compare_files(self):
        """Compara V1 e V2"""
        files = [
            "postgres_property_details.csv",
            "postgres_auction_events.csv",
            "postgres_property_auction_history.csv"
        ]
        
        ignore_cols = ["created_at", "updated_at"]
        results = {}
        all_identical = True
        
        for f in files:
            v1_path = os.path.join(self.temp_dir, f"v1_{f}")
            v2_path = os.path.join(self.temp_dir, f"v2_{f}")
            
            if not os.path.exists(v1_path) or not os.path.exists(v2_path):
                continue
            
            try:
                h1 = self.hash_csv(v1_path, ignore_cols)
                h2 = self.hash_csv(v2_path, ignore_cols)
                
                identical = h1 == h2
                results[f] = {
                    "identical": identical,
                    "hash_v1": h1,
                    "hash_v2": h2
                }
                
                if not identical:
                    all_identical = False
                    self.log("warning", f"{f}: DIFERENTE")
                else:
                    self.log("success", f"{f}: ✅ IDÊNTICO")
            except Exception as e:
                self.log("error", f"Erro ao comparar {f}: {e}")
                all_identical = False
        
        return results, all_identical
    
    def test_id_preservation(self):
        """Testa preservação de IDs"""
        self.log("info", "Testando preservação de IDs...")
        
        v1_props = pd.read_csv(os.path.join(self.temp_dir, "v1_postgres_property_details.csv"), dtype=str)
        v2_props = pd.read_csv(os.path.join(self.temp_dir, "v2_postgres_property_details.csv"), dtype=str)
        
        all_same = (v1_props['property_id'] == v2_props['property_id']).all()
        
        if all_same:
            self.log("success", f"✅ Todos os {len(v1_props):,} property_ids preservados")
        else:
            different = (v1_props['property_id'] != v2_props['property_id']).sum()
            self.log("warning", f"⚠️ {different:,} property_ids diferentes")
        
        return all_same
    
    def run(self):
        """Executa validação completa"""
        print("\n" + "="*80)
        print("🔍 VALIDADOR DE IDEMPOTÊNCIA - generate_postgres_csvs.py")
        print("="*80 + "\n")
        
        try:
            # Primeira execução
            if not self.run_generator("V1"):
                self.results["success"] = False
                return
            
            self.backup_current_files("v1")
            
            # Segunda execução
            if not self.run_generator("V2"):
                self.results["success"] = False
                return
            
            self.backup_current_files("v2")
            
            # Comparações
            print("\n" + "-"*80)
            print("Comparando arquivos...\n")
            
            file_results, files_identical = self.compare_files()
            self.results["tests"]["file_comparison"] = file_results
            
            if not files_identical:
                self.results["success"] = False
            
            # Preservação de IDs
            print("\n" + "-"*80)
            print("Validando preservação de IDs...\n")
            
            ids_preserved = self.test_id_preservation()
            self.results["tests"]["id_preservation"] = ids_preserved
            
            if not ids_preserved:
                self.results["success"] = False
            
            # Resultado final
            print("\n" + "="*80)
            if self.results["success"] and files_identical and ids_preserved:
                self.log("success", "✅ VALIDAÇÃO PASSOU - Sistema é 100% idempotente!")
            else:
                self.log("error", "❌ VALIDAÇÃO FALHOU - Verifique os logs acima")
            print("="*80 + "\n")
            
        except Exception as e:
            self.log("error", f"Erro fatal: {e}")
            import traceback
            traceback.print_exc()
            self.results["success"] = False
        
        finally:
            # Cleanup
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        
        return self.results["success"]

if __name__ == "__main__":
    validator = IdempotenceValidator()
    success = validator.run()
    sys.exit(0 if success else 1)
