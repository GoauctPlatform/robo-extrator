import os
import csv
import sys
import math

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
        print(f"Erro: {file_path} não encontrado.")
        return

    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)
    
    # Passo 1: contar as linhas utilizando o módulo csv para contar corretamente
    # no caso de existirem quebras de linha dentro dos próprios campos
    print(f"Contando as linhas do arquivo {file_path}...")
    total_data_rows = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print(f"Erro: {file_path} está vazio.")
            return
            
        for _ in reader:
            total_data_rows += 1
            
    if total_data_rows <= 0:
        print(f"Erro: {file_path} não possui linhas de dados (apenas cabeçalho).")
        return
        
    rows_per_part = math.ceil(total_data_rows / num_parts)
    print(f"Dividindo {file_path} em {num_parts} partes (aprox. {rows_per_part} linhas por parte)...")
    
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
            
    print(f"Finalizado a divisão do arquivo {file_path}.")

if __name__ == "__main__":
    # Lista dos arquivos que serão divididos
    files_to_split = [
        "postgres_auction_events.csv",
        "postgres_property_auction_history.csv",
        "postgres_property_details.csv"
    ]
    
    # Pasta onde os arquivos divididos serão salvos
    output_directory = "split_postgres_csvs"
    os.makedirs(output_directory, exist_ok=True)
    
    print("Iniciando o processo de divisão das planilhas...\n")
    for filename in files_to_split:
        split_csv(filename, output_directory)
        print("-" * 40)
        
    print(f"Todos os arquivos foram processados. Você pode conferir os resultados na pasta '{output_directory}'.")
