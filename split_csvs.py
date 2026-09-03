import os
import csv
import sys
import math

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Increase field size limit for large fields to avoid errors
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)

def split_csv(file_path, output_dir, num_parts=4):
    if not os.path.exists(file_path):
        print(f"❌ Erro: {file_path} não encontrado.")
        return False

    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)
    
    # Passo 1: contar as linhas utilizando o módulo csv para contar corretamente
    # no caso de existirem quebras de linha dentro dos próprios campos
    print(f"🔍 Contando as linhas do arquivo {file_path}...")
    total_data_rows = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print(f"❌ Erro: {file_path} está vazio.")
            return False
            
        for _ in reader:
            total_data_rows += 1
            
    if total_data_rows <= 0:
        print(f"❌ Erro: {file_path} não possui linhas de dados (apenas cabeçalho).")
        return False
        
    rows_per_part = math.ceil(total_data_rows / num_parts)
    print(f"✂️ Dividindo {file_path} em {num_parts} partes (total: {total_data_rows} linhas, aprox. {rows_per_part} linhas/parte)...")
    
    # Passo 2: Fazer a divisão real
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader) # Pula o cabeçalho
        
        current_part = 1
        current_row_count = 0
        out_f = None
        writer = None
        
        def open_new_part():
            nonlocal out_f, writer, current_part
            part_name = f"{name}_parte{current_part}{ext}"
            part_path = os.path.join(output_dir, part_name)
            out_f = open(part_path, 'w', encoding='utf-8', newline='')
            writer = csv.writer(out_f)
            writer.writerow(header) # Mantém o cabeçalho original
            
        open_new_part()
        
        for row in reader:
            writer.writerow(row)
            current_row_count += 1
            if current_row_count >= rows_per_part and current_part < num_parts:
                out_f.close()
                current_part += 1
                current_row_count = 0
                open_new_part()
                
        if out_f and not out_f.closed:
            out_f.close()
            
    print(f"✅ Finalizado com sucesso a divisão do arquivo {file_path} em {current_part} partes.")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("✂️  [DIVISÃO] Divisão dos CSVs PostgreSQL")
    print("=" * 60)
    
    # Lista dos arquivos que serão divididos
    files_to_split = [
        "postgres_auction_events.csv",
        "postgres_property_auction_history.csv",
        "postgres_property_details.csv"
    ]
    
    # Pasta onde os arquivos divididos serão salvos
    output_directory = "split_postgres_csvs"
    os.makedirs(output_directory, exist_ok=True)
    
    # Validação prévia de existência dos arquivos
    missing_files = [f for f in files_to_split if not os.path.exists(f)]
    if missing_files:
        print(f"\n❌ ERRO: {len(missing_files)} arquivo(s) necessário(s) não foram encontrados:")
        for mf in missing_files:
            print(f"   • {mf}")
        print("\n💡 Certifique-se de executar a Fase 3 (generate_postgres_csvs.py) antes de dividir.")
        sys.exit(1)
        
    success_count = 0
    for filename in files_to_split:
        if split_csv(filename, output_directory):
            success_count += 1
        print("-" * 50)
        
    if success_count == len(files_to_split):
        print(f"\n✅ SUCESSO: Todos os {success_count} arquivos foram divididos com sucesso!")
        print(f"📂 Arquivos disponíveis na pasta '{output_directory}'.")
        sys.exit(0)
    else:
        print(f"\n❌ ERRO: Apenas {success_count}/{len(files_to_split)} arquivos foram processados com sucesso.")
        sys.exit(1)

