import os
import uuid
import re
import hashlib
import shutil
from datetime import datetime
from glob import glob
import pandas as pd

# ============================================================
# CONFIGURACAO
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "all_parcels_enriched.csv")
OUT_AUCTIONS = os.path.join(BASE_DIR, "postgres_auction_events.csv")
OUT_PROPERTIES = os.path.join(BASE_DIR, "postgres_property_details.csv")
OUT_HISTORY = os.path.join(BASE_DIR, "postgres_property_auction_history.csv")

# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def is_valid_address(address):
    """Verifica se o endereço está no padrão aceito e completo."""
    if pd.isna(address) or not address:
        return False
    
    # Normalize address: remove commas, replace multiple spaces with single space, convert to uppercase
    address_str = str(address)
    address_clean = address_str.replace(',', ' ').strip()
    address_clean = re.sub(r'\s+', ' ', address_clean)
    
    # 1. Must start with a number (digits)
    if not re.match(r'^\d+', address_clean):
        return False
        
    # 2. Must end with a ZIP code (5 digits or 5+4 digits)
    if not re.search(r'\d{5}(-\d{4})?$', address_clean):
        return False
        
    # 3. Must have a 2-letter state code before the ZIP code
    if not re.search(r'\b[A-Z]{2}\s+\d{5}(-\d{4})?$', address_clean):
        return False
        
    # 4. Check middle words (street and city name)
    # Strip starting number and trailing State + Zip
    middle = re.sub(r'^\d+\s*', '', address_clean)
    middle = re.sub(r'\s+[A-Z]{2}\s+\d{5}(-\d{4})?$', '', middle)
    middle_words = middle.strip().split()
    
    # We expect at least a street name (1 word) and a city name (1 word) -> total >= 2 words
    if len(middle_words) < 2:
        return False
        
    return True


def load_previous_exports():
    """Carrega a exportação anterior mais recente."""
    prev_dirs = sorted(glob("previous_exports/*/"), reverse=True)
    if not prev_dirs:
        print("⚠️ Nenhuma exportação anterior encontrada.")
        return None, None
    
    prev_dir = prev_dirs[0]
    print(f"📂 Carregando exportação anterior de: {prev_dir}")
    
    try:
        props = pd.read_csv(f"{prev_dir}postgres_property_details.csv", dtype=str)
        auctions = pd.read_csv(f"{prev_dir}postgres_auction_events.csv", dtype=str)
        print(f"   ✅ {len(props):,} propriedades carregadas")
        print(f"   ✅ {len(auctions):,} leilões carregados")
        return props, auctions
    except FileNotFoundError as e:
        print(f"⚠️ Erro ao carregar exportações: {e}")
        return None, None

def generate_deterministic_uuid(key_tuple):
    """
    Gera UUID determinístico baseado em uma chave.
    Mesma chave SEMPRE gera mesmo UUID.
    """
    key_str = str(key_tuple)
    hash_hex = hashlib.md5(key_str.encode()).hexdigest()
    return str(uuid.UUID(hex=hash_hex))

def create_id_maps(prev_props, prev_auctions):
    """Cria mapas (chave -> id) a partir de exportações anteriores."""
    
    property_id_map = {}
    if prev_props is not None:
        for _, row in prev_props.iterrows():
            key = (
                str(row['parcel_id']).strip().lower(),
                str(row['county']).strip().lower(),
                str(row['state']).strip().upper()
            )
            property_id_map[key] = str(row['property_id'])
    
    auction_id_map = {}
    if prev_auctions is not None:
        for _, row in prev_auctions.iterrows():
            key = (
                str(row['name']).strip().lower(),
                str(row['state']).strip().upper(),
                str(row['auction_date']).strip()
            )
            auction_id_map[key] = int(row['id'])
    
    return property_id_map, auction_id_map

def backup_to_previous_exports(props_file, auctions_file, history_file):
    """Cria backup datado em previous_exports/"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_dir = f"previous_exports/{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    shutil.copy(props_file, f"{backup_dir}/{os.path.basename(props_file)}")
    shutil.copy(auctions_file, f"{backup_dir}/{os.path.basename(auctions_file)}")
    shutil.copy(history_file, f"{backup_dir}/{os.path.basename(history_file)}")
    
    print(f"✅ Backup criado em: {backup_dir}")

def clean_currency(value):
    """Converte valor monetario em string com '$' e ',' para float."""
    if pd.isna(value) or str(value).strip() == "":
        return None
    val_str = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(val_str)
    except ValueError:
        return None

def normalize_date(date_str):
    """Extrai e converte data para YYYY-MM-DD."""
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None
    
    date_str = str(date_str).strip()
    
    # Se ja estiver no formato YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
        return date_str[:10]
        
    MONTH_MAP = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        "january": "01", "february": "02", "march": "03", "april": "04",
        "june": "06", "july": "07", "august": "08", "september": "09",
        "october": "10", "november": "11", "december": "12",
    }
    
    s_lower = date_str.lower()
    year_m = re.search(r"\b(20\d{2})\b", s_lower)
    if not year_m:
        return None
    year = year_m.group(1)

    month = None
    for mon_str, mon_num in MONTH_MAP.items():
        if re.search(r"\b" + re.escape(mon_str) + r"\b", s_lower):
            month = mon_num
            break

    if not month:
        return None

    # Pega o primeiro numero de 1-2 digitos que NAO e o ano
    day_m = re.search(r"\b(\d{1,2})\b", s_lower)
    if not day_m:
        return f"{year}-{month}-01" # Default to 1st if no day found
    day = day_m.group(1).zfill(2)

    return f"{year}-{month}-{day}"

# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Lendo {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE, dtype=str)
    
    # ------------------------------------------------------------
    # FILTRO DE ENDEREÇOS INCOMPLETOS
    # ------------------------------------------------------------
    print("Executando validação de endereços...")
    initial_count = len(df)
    
    # Se não houver coluna Address, apenas pula o filtro para evitar quebra
    if "Address" in df.columns:
        mask_valid = df["Address"].apply(is_valid_address)
        df_incomplete = df[~mask_valid]
        
        if not df_incomplete.empty:
            incomplete_file = os.path.join(BASE_DIR, "incomplete_addresses.csv")
            df_incomplete.to_csv(incomplete_file, index=False)
            print(f"⚠️  Encontrados {len(df_incomplete):,} registros com endereços incompletos.")
            print(f"   Eles foram ISOLADOS/CONGELADOS e salvos em: {incomplete_file}")
        
        df = df[mask_valid].copy()
        print(f"✅ Mantidos {len(df):,} registros válidos (de um total original de {initial_count:,}).")
    else:
        print("⚠️  Coluna 'Address' não encontrada. Pulando validação.")
    
    print("-" * 80)
    
    NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("Processando tabela auction_events...")
    
    # Montar DataFrame de Leiloes (auctions)
    # Como as propriedades tem os dados do leilão em que participam, vamos dedubplicar na tabela de leiloes.
    
    # Colunas de leilão no enriched
    # Parcels: Auction Name (usaremos como name)
    # Combined adicionou: Name (nome_completo_no_combined), Short Name
    # E vamos usar 'Auction Name' se 'Name' estiver faltando
    
    # Tentar pegar o 'Name_c' (se existir) que era o nome completo, caso contrario usar o 'Auction Name'
    df["auction_final_name"] = df.get("Name_c", df["Auction Name"])
    
    auctions_cols = [
        "auction_final_name", "Short Name", "Auction Date", "Time", "Location", 
        "County", "County Code", "State", "Tax Status", "Notes", 
        "Search Link", "Register Date", "Register Link", "List Link", "Purchase Info Link",
        "Inventory Type" # Manter temporariamente para linkar propriedades depois
    ]
    
    # Extrair colunas q temos
    avail_cols = [c for c in auctions_cols if c in df.columns]
    
    df_auctions_raw = df[avail_cols].drop_duplicates()
    
    # Vamos agrupar leilões unicos baseados no nome, estado e data
    df_auctions_raw["norm_date"] = df_auctions_raw["Auction Date"].apply(normalize_date)
    df_auctions_unique = df_auctions_raw.drop_duplicates(subset=["auction_final_name", "State", "norm_date"]).copy()
    
    # Carregar exportações anteriores para preservar IDs de leilões
    prev_props, prev_auctions = load_previous_exports()
    property_id_map, auction_id_map = create_id_maps(prev_props, prev_auctions)
    
    print(f"\n🗺️ Mapas criados:")
    print(f"   Property ID map: {len(property_id_map):,} entradas")
    print(f"   Auction ID map: {len(auction_id_map):,} entradas\n")
    
    # Usar IDs anteriores se disponível, senão gerar novos
    auction_ids = []
    for _, row in df_auctions_unique.iterrows():
        key = (
            str(row['auction_final_name']).strip().lower(),
            str(row['State']).strip().upper(),
            str(row['norm_date']).strip()
        )
        
        if key in auction_id_map:
            # Usar ID anterior (preservado)
            auction_ids.append(auction_id_map[key])
        else:
            # Gerar novo ID (incrementar a partir do máximo anterior)
            max_id = max(auction_id_map.values()) if auction_id_map else 0
            new_id = max_id + len(auction_ids) + 1
            auction_ids.append(new_id)
    
    df_auctions_unique["id"] = auction_ids
    
    # Contar propriedades por leilão para o parcels_count
    # Match property to auction id using the same subset keys
    df["norm_date"] = df["Auction Date"].apply(normalize_date)
    
    # Merge para pegar o ID do leilão
    df = df.merge(
        df_auctions_unique[["auction_final_name", "State", "norm_date", "id"]],
        on=["auction_final_name", "State", "norm_date"],
        how="left",
    ).rename(columns={"id": "auction_id"})
    
    # Parcels count
    parcels_counts = df.groupby("auction_id").size().reset_index(name="parcels_count")
    df_auctions_unique = df_auctions_unique.merge(parcels_counts, left_on="id", right_on="auction_id", how="left")
    
    df_auctions_export = pd.DataFrame()
    df_auctions_export["id"] = df_auctions_unique["id"]
    df_auctions_export["name"] = df_auctions_unique["auction_final_name"]
    df_auctions_export["short_name"] = df_auctions_unique.get("Short Name")
    df_auctions_export["auction_date"] = df_auctions_unique["norm_date"]
    df_auctions_export["time"] = df_auctions_unique.get("Time")
    df_auctions_export["location"] = df_auctions_unique.get("Location")
    df_auctions_export["county"] = df_auctions_unique.get("County")
    df_auctions_export["county_code"] = df_auctions_unique.get("County Code")
    df_auctions_export["state"] = df_auctions_unique.get("State")
    df_auctions_export["tax_status"] = df_auctions_unique.get("Tax Status")
    df_auctions_export["parcels_count"] = df_auctions_unique["parcels_count"].fillna(0).astype(int)
    df_auctions_export["notes"] = df_auctions_unique.get("Notes")
    df_auctions_export["search_link"] = df_auctions_unique.get("Search Link")
    df_auctions_export["register_date"] = df_auctions_unique.get("Register Date")
    df_auctions_export["register_link"] = df_auctions_unique.get("Register Link")
    df_auctions_export["list_link"] = df_auctions_unique.get("List Link")
    df_auctions_export["purchase_info_link"] = df_auctions_unique.get("Purchase Info Link")
    df_auctions_export["created_at"] = NOW
    df_auctions_export["updated_at"] = NOW
    
    df_auctions_export.to_csv(OUT_AUCTIONS, index=False)
    print(f"Salvo {OUT_AUCTIONS} com {len(df_auctions_export)} registros de leilões.")

    
    print("Processando tabela property_details...")
    
    # Processar propriedades com preservação de IDs
    property_ids = []
    preserved_count = 0
    new_count = 0
    
    for idx, row in df.iterrows():
        key = (
            str(row["Parcel Number"]).strip().lower(),
            str(row["County"]).strip().lower(),
            str(row["State"]).strip().upper()
        )
        
        if key in property_id_map:
            # Usar ID anterior (preservado)
            prop_id = property_id_map[key]
            preserved_count += 1
        else:
            # Gerar UUID DETERMINÍSTICO para novos (idempotente)
            prop_id = generate_deterministic_uuid(key)
            new_count += 1
        
        property_ids.append(prop_id)
    
    print(f"📊 Propriedades:")
    print(f"   ✅ {preserved_count:,} IDs preservados")
    print(f"   🆕 {new_count:,} UUIDs novos gerados")
    print(f"   ⏭️ {len(df) - preserved_count - new_count:,} duplicatas processadas\n")
    
    df["property_id"] = property_ids
    
    df_properties = pd.DataFrame()
    
    # Colunas obrigatorias
    df_properties["property_id"] = df["property_id"]
    df_properties["parcel_id"] = df["Parcel Number"]
    df_properties["address"] = df["Address"]
    df_properties["county"] = df["County"]
    df_properties["state"] = df["State"]
    
    # Detalhes adicionais da propriedade
    df_properties["cs_number"] = df.get("C/S#")
    df_properties["pin"] = df.get("PIN")
    df_properties["owner_name"] = df.get("Name")
    df_properties["next_auction"] = df.get("Next Auction")
    
    # Info de Lote e Area
    df_properties["lot_acres"] = df["Acres"].apply(clean_currency)
    df_properties["property_type"] = df.get("Parcel Type")
    df_properties["land_value"] = df.get("Land").apply(clean_currency)
    df_properties["building_value"] = df.get("Building").apply(
        clean_currency
    )
    df_properties["occupancy_status"] = df.get("Occupancy")
    df_properties["amount_due"] = df["Amount Due"].apply(clean_currency)
    df_properties["assessed_value"] = df["Total Value"].apply(
        clean_currency
    )
    
    # Vemos colunas como "Sale Year", colocaremos em tax_year
    def safe_int(v):
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            return None
            
    df_properties["tax_year"] = df.get("Sale Year").apply(safe_int)
    
    # O campo Name: já mapeado em owner_name acima
    df_properties["owner_address"] = df.get("Name")
    
    # Status
    def set_availability(val):
        val = str(val).lower()
        if 'unavailable' in val and 'unavailable' == val:
            return 'unavailable'
        return 'available'
    
    df_properties["status"] = df["Status"]  # Quit Claim, etc
    df_properties["availability_status"] = (
        df["Availability"].apply(set_availability)
    )
    df_properties["property_category"] = df["Tax Status"].fillna(
        "Tax Deed"
    )
    df_properties["is_processed"] = False
    
    df_properties.to_csv(OUT_PROPERTIES, index=False)
    prop_count = len(df_properties)
    print(f"Salvo {OUT_PROPERTIES} com {prop_count} registros.")

    # Relacao Propriedades <-> Leilão (history)
    print("Gerando property_auction_history...")
    df_history = pd.DataFrame()
    df_history["property_id"] = df["property_id"]
    df_history["auction_eventId"] = df["auction_id"]
    df_history["created_at"] = NOW

    df_history = df_history.dropna(subset=["auction_eventId"])
    df_history["auction_eventId"] = (
        df_history["auction_eventId"].astype(int)
    )

    df_history.to_csv(OUT_HISTORY, index=False)
    history_count = len(df_history)
    print(f"Salvo {OUT_HISTORY} com {history_count} "
          "relacionamentos.")
    
    # Criar backup datado
    print("\n" + "="*80)
    backup_to_previous_exports(OUT_PROPERTIES, OUT_AUCTIONS, OUT_HISTORY)
    print("="*80 + "\n")
    
    print("✅ Processamento concluído com sucesso!")
    print(f"   Propriedades: {prop_count:,}")
    print(f"   Leilões: {len(df_auctions_export):,}")
    print(f"   Relacionamentos: {history_count:,}\n")


if __name__ == "__main__":
    main()
