"""
Script de reconciliação de arquivos PostgreSQL CSV.

Compara arquivos novos com versão baseline (legacy) e mantém IDs
consistentes para registros existentes, atribuindo novos IDs apenas
para dados completamente novos.
"""

import os
import pandas as pd
from datetime import datetime

# ============================================================
# CONFIGURACAO
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEGACY_DIR = os.path.join(BASE_DIR, "11.04.26")

# Arquivos versão 0 (baseline)
LEGACY_AUCTIONS = os.path.join(
    LEGACY_DIR, "postgres_auction_events.csv"
)
LEGACY_PROPERTIES = os.path.join(
    LEGACY_DIR, "postgres_property_details.csv"
)
LEGACY_HISTORY = os.path.join(
    LEGACY_DIR, "postgres_property_auction_history.csv"
)

# Arquivos versão 1 (novos)
NEW_AUCTIONS = os.path.join(BASE_DIR, "postgres_auction_events.csv")
NEW_PROPERTIES = os.path.join(BASE_DIR, "postgres_property_details.csv")
NEW_HISTORY = os.path.join(BASE_DIR, "postgres_property_auction_history.csv")

# Arquivos de saída (reconciliados)
OUT_AUCTIONS = os.path.join(BASE_DIR, "postgres_auction_events.csv")
OUT_AUCTIONS_NEW = os.path.join(
    BASE_DIR, "postgres_auction_events_NEW.csv"
)
OUT_PROPERTIES = os.path.join(BASE_DIR, "postgres_property_details.csv")
OUT_PROPERTIES_NEW = os.path.join(
    BASE_DIR, "postgres_property_details_NEW.csv"
)
OUT_HISTORY = os.path.join(BASE_DIR, "postgres_property_auction_history.csv")

# Arquivo de origem de dados enriquecidos
ENRICHED_FILE = os.path.join(BASE_DIR, "all_parcels_enriched.csv")


# ============================================================
# FUNCOES AUXILIARES
# ============================================================


def get_auction_key(row):
    """Cria chave única para identificar um leilão.
    
    Usa nome, estado e data como identificadores únicos.
    """
    return (
        str(row["name"]).strip().lower(),
        str(row["state"]).strip().upper(),
        str(row["auction_date"]).strip()
    )


def get_property_key(row):
    """Cria chave única para identificar uma propriedade.
    
    Usa parcel_id, county e state como identificadores únicos.
    """
    return (
        str(row["parcel_id"]).strip().lower(),
        str(row["county"]).strip().lower(),
        str(row["state"]).strip().upper()
    )


def get_enriched_key(row):
    """Cria chave única para uma linha no arquivo enriched.
    
    Usa Parcel Number como chave primária.
    """
    return str(row["Parcel Number"]).strip().lower()


# ============================================================
# MAIN
# ============================================================


def main():
    """Executa reconciliação completa dos arquivos."""
    print("=" * 70)
    print("RECONCILIAÇÃO DE ARQUIVOS POSTGRES CSV")
    print("=" * 70)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ================================================================
    # 1. CARREGAR ARQUIVOS LEGACY (VERSÃO 0)
    # ================================================================
    print("\n[1/6] Carregando arquivos legacy (versão 0)...")

    df_legacy_auctions = pd.read_csv(LEGACY_AUCTIONS, dtype=str)
    df_legacy_properties = pd.read_csv(LEGACY_PROPERTIES, dtype=str)
    df_legacy_history = pd.read_csv(LEGACY_HISTORY, dtype=str)

    print(f"  - Leilões legacy: {len(df_legacy_auctions)} registros")
    print(
        f"  - Propriedades legacy: {len(df_legacy_properties)} registros"
    )
    print(f"  - Histórico legacy: {len(df_legacy_history)} registros")

    # Criar mapas de identidade legacy
    auction_legacy_map = {}  # (name, state, date) -> id
    for _, row in df_legacy_auctions.iterrows():
        key = get_auction_key(row)
        auction_legacy_map[key] = str(row["id"])

    property_legacy_map = {}  # (parcel_id, county, state) -> property_id
    for _, row in df_legacy_properties.iterrows():
        key = get_property_key(row)
        property_legacy_map[key] = str(row["property_id"])

    print(f"  - Mapa leilões: {len(auction_legacy_map)} chaves")
    print(f"  - Mapa propriedades: {len(property_legacy_map)} chaves")

    # ================================================================
    # 2. CARREGAR ARQUIVOS NOVOS (VERSÃO 1)
    # ================================================================
    print("\n[2/6] Carregando arquivos novos (versão 1)...")

    df_new_auctions = pd.read_csv(NEW_AUCTIONS, dtype=str)
    df_new_properties = pd.read_csv(NEW_PROPERTIES, dtype=str)
    
    # Tentar carregar histórico; se vazio, criar DataFrame vazio com
    # colunas corretas
    try:
        df_new_history = pd.read_csv(NEW_HISTORY, dtype=str)
    except pd.errors.EmptyDataError:
        # Arquivo vazio: criar DataFrame com colunas do legacy
        df_legacy_history = pd.read_csv(
            os.path.join(LEGACY_DIR, "postgres_property_auction_history.csv"),
            dtype=str,
            nrows=0
        )
        df_new_history = df_legacy_history.copy()

    print(f"  - Leilões novos: {len(df_new_auctions)} registros")
    print(f"  - Propriedades novas: {len(df_new_properties)} registros")
    print(f"  - Histórico novo: {len(df_new_history)} registros")

    # ================================================================
    # 3. RECONCILIAR LEILÕES (AUCTIONS)
    # ================================================================
    print("\n[3/6] Reconciliando leilões...")

    df_auctions_reconciled = df_new_auctions.copy()

    # Próximo ID para novos leilões
    max_auction_id = int(df_legacy_auctions["id"].astype(int).max())
    next_auction_id = max_auction_id + 1

    # Mapa para remapear auction IDs
    auction_id_remap = {}

    # Listas para separar atualizações e novos
    auctions_updated = []
    auctions_new_list = []

    auctions_kept = 0
    auctions_new = 0

    for idx, row in df_auctions_reconciled.iterrows():
        key = get_auction_key(row)

        if key in auction_legacy_map:
            # Leilão já existe: manter ID antigo
            old_id = int(auction_legacy_map[key])
            df_auctions_reconciled.at[idx, "id"] = str(old_id)
            auction_id_remap[str(row["id"])] = str(old_id)
            auctions_kept += 1
            auctions_updated.append(idx)
        else:
            # Leilão novo: atribuir novo ID sequencial
            df_auctions_reconciled.at[idx, "id"] = str(next_auction_id)
            auction_id_remap[str(row["id"])] = str(next_auction_id)
            auctions_new += 1
            auctions_new_list.append(idx)
            next_auction_id += 1

    # Atualizar timestamps
    df_auctions_reconciled["updated_at"] = now

    print(f"  - Leilões mantidos: {auctions_kept}")
    print(f"  - Leilões novos: {auctions_new}")
    print(f"  - Total leilões: {len(df_auctions_reconciled)}")

    # ================================================================
    # 4. RECONCILIAR PROPRIEDADES (PROPERTIES)
    # ================================================================
    print("\n[4/6] Reconciliando propriedades...")

    df_properties_reconciled = df_new_properties.copy()

    # Mapa para remapear property IDs
    property_id_remap = {}

    # Listas para separar atualizações e novos
    properties_updated = []
    properties_new_list = []

    properties_kept = 0
    properties_new = 0

    for idx, row in df_properties_reconciled.iterrows():
        key = get_property_key(row)

        if key in property_legacy_map:
            # Propriedade já existe: manter ID antigo
            old_property_id = property_legacy_map[key]
            df_properties_reconciled.at[idx, "property_id"] = (
                old_property_id
            )
            property_id_remap[str(row["property_id"])] = old_property_id
            properties_kept += 1
            properties_updated.append(idx)
        else:
            # Propriedade nova: manter UUID gerado
            old_uuid = str(row["property_id"])
            property_id_remap[old_uuid] = old_uuid
            properties_new += 1
            properties_new_list.append(idx)

    print(f"  - Propriedades mantidas: {properties_kept}")
    print(f"  - Propriedades novas: {properties_new}")
    print(f"  - Total propriedades: {len(df_properties_reconciled)}")

    # ================================================================
    # 5. RECONCILIAR HISTÓRICO (HISTORY)
    # ================================================================
    print("\n[5/6] Reconciliando histórico de leilões...")

    # IMPORTANTE: Começar com histórico LEGACY como base
    # para manter os IDs antigos dos relacionamentos
    df_history_reconciled = df_legacy_history.copy()

    # Rastrear quais property e auction IDs são novos
    new_property_ids = set()  # IDs que viram novos na reconciliação
    new_auction_ids = set()  # IDs que viram novos na reconciliação

    for idx, row in df_new_properties.iterrows():
        old_uuid = str(row["property_id"])
        if old_uuid in property_id_remap:
            new_id = property_id_remap[old_uuid]
            # É novo se o UUID não estava no property_legacy_map
            key = get_property_key(row)
            if key not in property_legacy_map:
                new_property_ids.add(new_id)

    for idx, row in df_new_auctions.iterrows():
        old_id = str(row["id"])
        if old_id in auction_id_remap:
            new_id = auction_id_remap[old_id]
            # É novo se não estava no auction_legacy_map
            key = get_auction_key(row)
            if key not in auction_legacy_map:
                new_auction_ids.add(new_id)

    # Remapear property_id e auction_id conforme mapas criados
    for idx, row in df_history_reconciled.iterrows():
        old_property_id = str(row["property_id"])
        old_auction_id = str(row["auction_eventId"])

        if old_property_id in property_id_remap:
            df_history_reconciled.at[idx, "property_id"] = (
                property_id_remap[old_property_id]
            )

        if old_auction_id in auction_id_remap:
            df_history_reconciled.at[idx, "auction_eventId"] = (
                auction_id_remap[old_auction_id]
            )

    # IMPORTANTE: NÃO FILTRAR O HISTÓRICO LEGACY!
    # O histórico é começado com todos os records legacy.
    # Novos relacionamentos serão ADICIONADOS depois (seções 5A/5B)
    # 
    # Contar histórico legacy como baseline
    history_baseline = len(df_history_reconciled)
    print(f"  - Histórico baseline (legacy): {history_baseline}")

    # ================================================================
    # 6. SALVAR ARQUIVOS RECONCILIADOS
    # ================================================================
    print("\n[6/6] Salvando arquivos reconciliados...")

    # Separar atualizações e novos registros
    df_auctions_updated = df_auctions_reconciled.iloc[
        auctions_updated
    ].copy()
    df_auctions_new = df_auctions_reconciled.iloc[auctions_new_list].copy()

    df_properties_updated = df_properties_reconciled.iloc[
        properties_updated
    ].copy()
    df_properties_new = df_properties_reconciled.iloc[
        properties_new_list
    ].copy()

    # ================================================================
    # 4.5. RE-ADICIONAR PROPRIEDADES LEGACY NÃO EM ENRICHED
    # ================================================================
    # Propriedades que existem no legacy mas não em (enriched + novo)
    current_props_ids = set(df_properties_reconciled["property_id"])
    legacy_props_ids = set(df_legacy_properties["property_id"])
    readded_props_ids = legacy_props_ids - current_props_ids

    if len(readded_props_ids) > 0:
        # Propriedades do legacy que não estão em novo
        df_readded_props = df_legacy_properties[
            df_legacy_properties["property_id"].isin(readded_props_ids)
        ].copy()

        # Adicionar ao conjunto reconciliado
        df_properties_reconciled = pd.concat(
            [df_properties_reconciled, df_readded_props],
            ignore_index=True
        )

        # Adicionar à lista para serem salvas
        readded_indices = list(range(
            len(df_properties_reconciled) - len(df_readded_props),
            len(df_properties_reconciled)
        ))
        properties_updated.extend(readded_indices)

        print(f"  [4.5/6] Re-adicionadas {len(df_readded_props)} "
              "propriedades legacy")

    # ================================================================
    # 5A. RECONSTRUIR HISTÓRICO PARA NOVAS PROPRIEDADES
    # ================================================================
    print("\n[5A/6] Reconstruindo histórico para propriedades novas...")

    if len(df_properties_new) > 0:
        try:
            df_enriched = pd.read_csv(ENRICHED_FILE, dtype=str)
            print("     Arquivo enriched carregado")

            # Mapa: parcel_id -> enriched_row
            enriched_parcel_map = {}
            for idx, row in df_enriched.iterrows():
                parcel_num = str(row["Parcel Number"]).strip().lower()
                enriched_parcel_map[parcel_num] = row

            # Mapa: nome normalizado -> ID
            new_auction_names = {}
            for idx, row in df_auctions_reconciled.iterrows():
                auction_name = str(row["name"]).strip().lower()
                new_auction_names[auction_name] = str(row["id"])

            # Para cada propriedade nova, buscar leilão no enriched
            new_history_records = []

            for idx, prop_row in df_properties_new.iterrows():
                prop_parcel_id = str(
                    prop_row["parcel_id"]
                ).strip().lower()
                prop_property_id = str(prop_row["property_id"])

                # Buscar no enriched
                if prop_parcel_id in enriched_parcel_map:
                    enriched_row = enriched_parcel_map[prop_parcel_id]

                    # Tentar encontrar leilão
                    auction_name = enriched_row.get(
                        "Name_c", enriched_row.get("Auction Name")
                    )
                    if pd.isna(auction_name):
                        auction_name = enriched_row.get("Auction Name")

                    # Normalizar nome para matching
                    auction_name_norm = str(
                        auction_name
                    ).strip().lower()

                    # Buscar ID do leilão
                    auction_id = None
                    if auction_name_norm in new_auction_names:
                        auction_id = new_auction_names[auction_name_norm]

                    if auction_id:
                        # Adicionar à lista de novo histórico
                        new_history_records.append(
                            {
                                "property_id": prop_property_id,
                                "auction_eventId": str(int(auction_id)),
                                "created_at": now,
                            }
                        )

            # Adicionar ao histórico
            if new_history_records:
                df_new_history_enriched = pd.DataFrame(
                    new_history_records
                )
                df_history_reconciled = pd.concat(
                    [
                        df_history_reconciled,
                        df_new_history_enriched,
                    ],
                    ignore_index=True,
                )
                print(
                    f"     Adicionados {len(new_history_records)} "
                    "históricos de novas propriedades"
                )
            else:
                print(
                    "     Nenhuma propriedade nova encontrada no enriched"
                )

            # ============================================================
            # 5B. RECONSTRUIR HISTÓRICO PARA PROPRIEDADES ATUALIZADAS
            #     COM LEILÕES NOVOS
            # ============================================================
            print(
                "     Verificando propriedades ATUALIZADAS com "
                "leilões NOVOS..."
            )

            # Mapa de leilões novos
            new_auction_ids = set(df_auctions_new["id"].astype(str))

            updated_history_records = []

            for idx, prop_row in df_properties_updated.iterrows():
                prop_parcel_id = str(
                    prop_row["parcel_id"]
                ).strip().lower()
                prop_property_id = str(prop_row["property_id"])

                # Buscar no enriched
                if prop_parcel_id in enriched_parcel_map:
                    enriched_row = enriched_parcel_map[prop_parcel_id]

                    # Tentar encontrar leilão
                    auction_name = enriched_row.get(
                        "Name_c", enriched_row.get("Auction Name")
                    )
                    if pd.isna(auction_name):
                        auction_name = enriched_row.get("Auction Name")

                    # Normalizar nome
                    auction_name_norm = str(
                        auction_name
                    ).strip().lower()

                    # Buscar ID do leilão
                    auction_id = None
                    if auction_name_norm in new_auction_names:
                        auction_id = new_auction_names[auction_name_norm]

                    # Adicionar APENAS se o leilão é novo
                    if (
                        auction_id
                        and str(int(auction_id)) in new_auction_ids
                    ):
                        # IMPORTANTE: NÃO REMOVER históricos antigos!
                        # Apenas ADICIONAR o novo vínculo
                        # Isso mantém o histórico completo de auctions
                        # por que uma propriedade pode ter tido múltiplos
                        # leilões ao longo do tempo
                        
                        # Adicionar novo vínculo (sem remover antigos)
                        updated_history_records.append(
                            {
                                "property_id": prop_property_id,
                                "auction_eventId": (
                                    str(int(auction_id))
                                ),
                                "created_at": now,
                            }
                        )

            # Adicionar ao histórico
            if updated_history_records:
                df_updated_history = pd.DataFrame(
                    updated_history_records
                )
                df_history_reconciled = pd.concat(
                    [
                        df_history_reconciled,
                        df_updated_history,
                    ],
                    ignore_index=True,
                )
                print(
                    f"     Adicionados {len(updated_history_records)} "
                    "históricos de propriedades ATUALIZADAS com "
                    "leilões NOVOS"
                )
            else:
                print(
                    "     Nenhuma propriedade ATUALIZADA com leilão "
                    "NOVO encontrada"
                )

        except FileNotFoundError:
            print(
                "     AVISO: all_parcels_enriched.csv não encontrado"
            )
    else:
        print("     Nenhuma propriedade nova a processar")

    # ================================================================
    # 5C. RESTAURAR HISTÓRICO PARA PROPRIEDADES RE-ADICIONADAS
    # ================================================================
    # Propriedades que foram re-adicionadas do legacy precisam de seus
    # históricos também restaurados
    if len(readded_props_ids) > 0:
        print("\n[5C/6] Restaurando histórico para "
              "propriedades re-adicionadas...")

        # Históricos no legacy para essas propriedades
        df_readded_hist = df_legacy_history[
            df_legacy_history["property_id"].isin(readded_props_ids)
        ].copy()

        # Remapear auction IDs se necessário
        for idx, row in df_readded_hist.iterrows():
            old_auction_id = str(row["auction_eventId"])
            if old_auction_id in auction_id_remap:
                df_readded_hist.at[idx, "auction_eventId"] = (
                    auction_id_remap[old_auction_id]
                )

        if len(df_readded_hist) > 0:
            df_history_reconciled = pd.concat(
                [df_history_reconciled, df_readded_hist],
                ignore_index=True
            )
            print(f"     Adicionados {len(df_readded_hist)} históricos "
                  "de propriedades re-adicionadas")

    # ================================================================
    # 6. SALVAR ARQUIVOS RECONCILIADOS
    # ================================================================
    print("\n[6/6] Salvando arquivos reconciliados...")
    df_auctions_updated.to_csv(OUT_AUCTIONS, index=False)
    print(f"  ✓ {OUT_AUCTIONS} ({len(df_auctions_updated)} atualizações)")

    # Salvar leilões (NOVOS)
    df_auctions_new.to_csv(OUT_AUCTIONS_NEW, index=False)
    print(f"  ✓ {OUT_AUCTIONS_NEW} ({len(df_auctions_new)} novos)")

    # Salvar propriedades (ATUALIZAÇÕES)
    df_properties_updated.to_csv(OUT_PROPERTIES, index=False)
    print(f"  ✓ {OUT_PROPERTIES} ({len(df_properties_updated)} atualizações)")

    # Salvar propriedades (NOVOS)
    df_properties_new.to_csv(OUT_PROPERTIES_NEW, index=False)
    print(f"  ✓ {OUT_PROPERTIES_NEW} ({len(df_properties_new)} novos)")

    # Salvar histórico
    df_history_reconciled.to_csv(OUT_HISTORY, index=False)
    print(f"  ✓ {OUT_HISTORY}")

    # ================================================================
    # RELATÓRIO FINAL
    # ================================================================
    print("\n" + "=" * 70)
    print("RECONCILIAÇÃO CONCLUÍDA COM SUCESSO")
    print("=" * 70)
    print("\nResumo:")
    print("  Leilões:")
    print(f"    - Mantidos: {auctions_kept}")
    print(f"    - Novos: {auctions_new}")
    print(f"    - Total: {len(df_auctions_reconciled)}")
    print("\n  Propriedades:")
    print(f"    - Mantidas: {properties_kept}")
    print(f"    - Novas: {properties_new}")
    print(f"    - Total: {len(df_properties_reconciled)}")
    print("\n  Histórico:")
    novo_count = len(df_history_reconciled)
    print(f"    - Relacionamentos totais: {novo_count}")
    print(f"    - Baseline (legacy): {history_baseline}")

    # ================================================================
    # 7. GERAR RELATÓRIO DE PROPRIEDADES ÓRFÃS
    # ================================================================
    print("\n[7/7] Gerando relatório de propriedades órfãs...")

    # IDs de propriedades novas
    new_props_ids = set(df_properties_new["property_id"])

    # IDs de propriedades no histórico (considerar DataFrame vazio)
    if len(df_history_reconciled) > 0:
        history_props_ids = set(df_history_reconciled["property_id"])
    else:
        history_props_ids = set()

    # Propriedades novas sem relacionamento
    orphaned_ids = new_props_ids - history_props_ids

    if orphaned_ids:
        # Pegar informações das propriedades órfãs
        df_orphaned = df_properties_new[
            df_properties_new["property_id"].isin(orphaned_ids)
        ].copy()

        # Gerar relatório
        report_path = os.path.join(
            BASE_DIR, "relatorio_propriedades_orfas.txt"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(
                "RELATÓRIO DE PROPRIEDADES ÓRFÃS\n"
                "(Propriedades sem relacionamento no histórico)\n"
            )
            f.write("=" * 80 + "\n\n")
            f.write(f"Data: {now}\n")
            f.write(f"Total de propriedades órfãs: {len(orphaned_ids)}\n")
            f.write(f"Total de propriedades novas: {properties_new}\n")
            if properties_new > 0:
                percentage = (
                    len(orphaned_ids) / properties_new * 100
                )
                f.write(f"Percentual: {percentage:.1f}%\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("DETALHES DAS PROPRIEDADES ÓRFÃS:\n")
            f.write("=" * 80 + "\n\n")

            for idx, row in df_orphaned.iterrows():
                f.write(f"Property ID: {row['property_id']}\n")
                f.write(f"Parcel ID: {row['parcel_id']}\n")
                f.write(f"Address: {row['address']}\n")
                f.write(f"County: {row['county']}\n")
                f.write(f"State: {row['state']}\n")
                f.write(f"Owner: {row['owner_name']}\n")
                f.write(f"Next Auction: {row['next_auction']}\n")
                f.write(f"Amount Due: {row['amount_due']}\n")
                f.write(f"Assessed Value: {row['assessed_value']}\n")
                f.write("-" * 80 + "\n\n")

        print(f"  ✓ {report_path}")
        print(f"    - {len(orphaned_ids)} propriedades órfãs identificadas")
    else:
        print("  ✓ Nenhuma propriedade órfã encontrada")

    # ================================================================
    # 8. GERAR ARQUIVO DE HISTÓRICO PARA DADOS NOVOS
    # ================================================================
    print("\n[8/8] Gerando postgres_property_auction_history_NEW.csv...")

    # Carregar IDs novos
    df_props_new = pd.read_csv(OUT_PROPERTIES_NEW, dtype=str)
    df_auctions_new = pd.read_csv(OUT_AUCTIONS_NEW, dtype=str)

    new_prop_ids = set(df_props_new["property_id"])
    new_auction_ids = set(df_auctions_new["id"].astype(str))

    # Filtrar histórico para apenas relacionamentos novos
    # (propriedade nova OU leilão novo)
    df_history_new_only = df_history_reconciled[
        (df_history_reconciled["property_id"].isin(new_prop_ids))
        | (df_history_reconciled["auction_eventId"].isin(new_auction_ids))
    ].copy()

    # Salvar histórico _NEW
    out_history_new = os.path.join(
        BASE_DIR, "postgres_property_auction_history_NEW.csv"
    )
    df_history_new_only.to_csv(out_history_new, index=False)

    print(f"  ✓ {out_history_new}")
    print(f"    - {len(df_history_new_only)} relacionamentos novos")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
