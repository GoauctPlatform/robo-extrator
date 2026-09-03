import pandas as pd
import os

# Diretório com os arquivos CSV
csv_directory = "./parcelfair_csv_auctions"
output_file = "./combined_auctions_data.csv"

# Verificar se o diretório existe
if not os.path.exists(csv_directory):
    print(f"Erro: Diretório '{csv_directory}' não encontrado.")
    exit(1)

# Listar todos os arquivos CSV
csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv')]

if not csv_files:
    print(f"Nenhum arquivo CSV encontrado em '{csv_directory}'")
    exit(1)

print(f"Encontrados {len(csv_files)} arquivos CSV")

# Ler e combinar todos os arquivos
dataframes = []
for csv_file in sorted(csv_files):
    file_path = os.path.join(csv_directory, csv_file)
    try:
        print(f"  Lendo: {csv_file}")
        df = pd.read_csv(file_path)
        dataframes.append(df)
    except Exception as e:
        print(f"  Erro ao ler {csv_file}: {str(e)}")

# Combinar todos os dataframes
if dataframes:
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Salvar o arquivo combinado
    combined_df.to_csv(output_file, index=False)
    print(f"\n✓ Sucesso! Arquivo criado: {output_file}")
    print(f"  Total de linhas: {len(combined_df)}")
    print(f"  Total de colunas: {len(combined_df.columns)}")
    print(f"\nColunas: {list(combined_df.columns)}")
else:
    print("Nenhum arquivo foi combinado com sucesso.")
