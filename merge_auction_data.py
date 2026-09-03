"""
merge_auction_data.py
=====================
Combina os CSVs de parcels (parcelfair_auction_parcels_csvs/) com o
combined_auctions_data.csv, enriquecendo cada parcel com os metadados
completos de seu leilão.

ESTRATÉGIA DE JOIN
------------------
Chave primária  : parcels["Auction Name"]  == combined["Short Name"]
                  parcels["State"]         == combined["State"]
Chave secundária: parcels["Auction Date"] normalizado == combined["Auction Date"]
                  (usado como desempate quando Short Name + State não é único,
                   ex: leilões de foreclosure semanais na Flórida)

FLUXO
-----
1. Lê e concatena todos os CSVs de parcels  → all_parcels_combined.csv
2. Lê e deduplicata o combined_auctions_data.csv
3. Normaliza as datas para formato YYYY-MM-DD
4. Executa o LEFT JOIN em três tentativas progressivas:
     a) Short Name + State + Auction Date completa  (mais preciso)
     b) Short Name + State + Year-Month             (fallback)
     c) Short Name + State                          (fallback final)
5. Grava all_parcels_enriched.csv + merge_report.txt

SAÍDAS
------
  all_parcels_combined.csv   → todos os parcels unificados (sem enriquecimento)
  all_parcels_enriched.csv   → parcels + colunas do combined após join
  merge_report.txt           → relatório detalhado com estatísticas
"""

import os
import re
import glob
import warnings
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
PARCELS_DIR   = os.path.join(BASE_DIR, "parcelfair_auction_parcels_csvs")
COMBINED_FILE = os.path.join(BASE_DIR, "combined_auctions_data.csv")
OUT_ALL       = os.path.join(BASE_DIR, "all_parcels_combined.csv")
OUT_ENRICHED  = os.path.join(BASE_DIR, "all_parcels_enriched.csv")
REPORT_FILE   = os.path.join(BASE_DIR, "merge_report.txt")

# Colunas do combined que serão adicionadas ao CSV final
COMBINED_COLS_TO_ADD = [
    "Search Link",
    "Name",          # Nome completo do leilão
    "Tax Status",
    "Parcels",
    "County Code",
    "County Name",
    "Time",
    "Location",
    "Notes",
    "Register Date",
    "Register Link",
    "List Link",
    "Purchase Info Link",
    "Register Link",
]

# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZAÇÃO DE DATAS
# ─────────────────────────────────────────────────────────────────────────────

_MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08", "september": "09",
    "october": "10", "november": "11", "december": "12",
}


def normalize_date(s: str) -> str | None:
    """
    Converte qualquer formato de data para YYYY-MM-DD.

    Suporta:
      '2026-03-02'                     → '2026-03-02'
      'Mar 2 (Monday) March 2026'      → '2026-03-02'
      'Apr 6 (Monday) April 2026'      → '2026-04-06'
    Retorna None se não conseguir parsear.
    """
    s = str(s).strip()

    # Já está em YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    s_lower = s.lower()

    year_m = re.search(r"\b(20\d{2})\b", s_lower)
    if not year_m:
        return None
    year = year_m.group(1)

    month = None
    for mon_str, mon_num in _MONTH_MAP.items():
        if re.search(r"\b" + re.escape(mon_str) + r"\b", s_lower):
            month = mon_num
            break

    if not month:
        return None

    # Pega o primeiro número de 1-2 dígitos que NÃO é o ano
    day_m = re.search(r"\b(\d{1,2})\b", s_lower)
    if not day_m:
        return None
    day = day_m.group(1).zfill(2)

    return f"{year}-{month}-{day}"


def year_month(date_normalized: str | None) -> str | None:
    """Retorna 'YYYY-MM' a partir de uma data normalizada."""
    if date_normalized and len(date_normalized) >= 7:
        return date_normalized[:7]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# LOG
# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str, fp=None):
    print(msg)
    if fp:
        fp.write(msg + "\n")
        fp.flush()


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1 — Carregar e unir todos os CSVs de parcels
# ─────────────────────────────────────────────────────────────────────────────

def load_all_parcels(parcels_dir: str, report_fp) -> pd.DataFrame:
    pattern = os.path.join(parcels_dir, "parcelfair_auction_parcels_*.csv")
    csv_files = sorted(glob.glob(pattern))

    if not csv_files:
        raise FileNotFoundError(f"Nenhum CSV encontrado em: {parcels_dir}")

    frames = []
    for f in csv_files:
        state_code = (
            os.path.basename(f)
            .replace("parcelfair_auction_parcels_", "")
            .replace(".csv", "")
        )
        try:
            df = pd.read_csv(f, dtype=str, keep_default_na=False)
            df["_source_file"] = state_code
            frames.append(df)
            log(f"    ✓ {state_code}: {len(df):>7,} parcels", report_fp)
        except Exception as e:
            log(f"    ✗ Erro ao ler {f}: {e}", report_fp)

    combined = pd.concat(frames, ignore_index=True)

    # Normaliza a data dos parcels
    combined["_date_norm"] = combined["Auction Date"].apply(normalize_date)
    combined["_year_month"] = combined["_date_norm"].apply(year_month)

    # Garante que State está limpo e Auction Name sem espaços duplos
    combined["State"] = combined["State"].str.strip()
    combined["Auction Name"] = combined["Auction Name"].str.strip().str.replace(r"\s+", " ", regex=True)

    return combined


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2 — Preparar o combined_auctions_data
# ─────────────────────────────────────────────────────────────────────────────

def prepare_combined(combined_file: str, report_fp) -> pd.DataFrame:
    df = pd.read_csv(combined_file, dtype=str, keep_default_na=False)
    log(f"  Registros originais : {len(df):,}", report_fp)

    # Deduplicar: remover linhas 100% idênticas
    df = df.drop_duplicates()
    log(f"  Após deduplicação  : {len(df):,}", report_fp)

    df["State"] = df["State"].str.strip()
    # Normaliza espaços múltiplos no Short Name (ex: "Brazoria Sheriff Sale  (PBFCM)" -> "Brazoria Sheriff Sale (PBFCM)")
    df["_short_name"] = df["Short Name"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["_date_norm"] = df["Auction Date"].apply(normalize_date)
    df["_year_month"] = df["_date_norm"].apply(year_month)

    # Filtrar apenas as colunas úteis para o join + as que serão adicionadas
    keep = ["_short_name", "State", "_date_norm", "_year_month"] + [
        c for c in COMBINED_COLS_TO_ADD if c in df.columns
    ]
    # Remove duplicatas de colunas keep (ex: Register Link aparece 2x na lista)
    keep = list(dict.fromkeys(keep))
    return df[keep].copy()


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3 — LEFT JOIN progressivo (3 tentativas)
# ─────────────────────────────────────────────────────────────────────────────

def left_join_progressive(df_parcels: pd.DataFrame, df_combined: pd.DataFrame, report_fp) -> pd.DataFrame:
    """
    Estratégia em 3 camadas para maximizar o match sem explosão de linhas:

    Pass 1 — Short Name + State + Data completa (YYYY-MM-DD)
    Pass 2 — Short Name + State + Ano-Mês (YYYY-MM)   [para parcels já sem match]
    Pass 3 — Short Name + State                        [fallback para o restante]

    Leilões sem nenhum match ficam com as colunas do combined em branco.
    """
    total = len(df_parcels)

    # Coluna auxiliar para controlar quais parcels já foram resolvidos
    df_parcels = df_parcels.copy()
    df_parcels["_idx"] = range(total)

    result_frames = []
    unmatched_mask = pd.Series([True] * total, index=df_parcels.index)

    # ── Pass 1: data completa ──────────────────────────────────────────────
    key_p1_l = ["Auction Name", "State", "_date_norm"]
    key_p1_r = ["_short_name",  "State", "_date_norm"]

    sub = df_parcels[unmatched_mask]
    merged_p1 = sub.merge(
        df_combined.drop_duplicates(subset=key_p1_r),
        left_on=key_p1_l,
        right_on=key_p1_r,
        how="inner",
        suffixes=("", "_c"),
    )
    # Garantir sem duplicatas após o join
    merged_p1 = merged_p1.drop_duplicates(subset=["_idx"])
    matched_p1 = set(merged_p1["_idx"])
    result_frames.append(merged_p1)
    unmatched_mask = df_parcels["_idx"].apply(lambda x: x not in matched_p1)
    log(f"  Pass 1 (data exata)  : {len(merged_p1):>8,} parcels", report_fp)

    # ── Pass 2: year-month ────────────────────────────────────────────────
    key_p2_l = ["Auction Name", "State", "_year_month"]
    key_p2_r = ["_short_name",  "State", "_year_month"]

    sub = df_parcels[unmatched_mask]
    merged_p2 = sub.merge(
        df_combined.drop_duplicates(subset=key_p2_r),
        left_on=key_p2_l,
        right_on=key_p2_r,
        how="inner",
        suffixes=("", "_c"),
    )
    merged_p2 = merged_p2.drop_duplicates(subset=["_idx"])
    matched_p2 = set(merged_p2["_idx"])
    result_frames.append(merged_p2)
    unmatched_mask = df_parcels["_idx"].apply(lambda x: x not in matched_p1 and x not in matched_p2)
    log(f"  Pass 2 (year-month)  : {len(merged_p2):>8,} parcels", report_fp)

    # ── Pass 3: Short Name + State ────────────────────────────────────────
    key_p3_l = ["Auction Name", "State"]
    key_p3_r = ["_short_name",  "State"]

    sub = df_parcels[unmatched_mask]
    merged_p3 = sub.merge(
        df_combined.drop_duplicates(subset=key_p3_r),
        left_on=key_p3_l,
        right_on=key_p3_r,
        how="inner",
        suffixes=("", "_c"),
    )
    merged_p3 = merged_p3.drop_duplicates(subset=["_idx"])
    matched_p3 = set(merged_p3["_idx"])
    result_frames.append(merged_p3)
    unmatched_mask = df_parcels["_idx"].apply(
        lambda x: x not in matched_p1 and x not in matched_p2 and x not in matched_p3
    )
    log(f"  Pass 3 (nome+estado) : {len(merged_p3):>8,} parcels", report_fp)

    # ── Sem match: adiciona como LEFT JOIN com NaN nas colunas do combined ─
    remain = df_parcels[unmatched_mask].copy()
    log(f"  Sem match            : {len(remain):>8,} parcels", report_fp)

    # Juntar tudo
    all_results = pd.concat(result_frames + [remain], ignore_index=True)

    # Verificar integridade: total deve ser igual ao original
    assert len(all_results) == total, (
        f"ERRO: total após merge ({len(all_results)}) ≠ original ({total})"
    )

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 4 — Organizar colunas e salvar
# ─────────────────────────────────────────────────────────────────────────────

def organize_and_save(merged: pd.DataFrame, parcels_original_cols: list, report_fp):
    # Remover colunas auxiliares internas (começam com _)
    drop_cols = [c for c in merged.columns if c.startswith("_")]
    merged = merged.drop(columns=drop_cols, errors="ignore")

    # Remover colunas duplicadas geradas pelo merge (_c suffix)
    c_suffix_cols = [c for c in merged.columns if c.endswith("_c")]
    merged = merged.drop(columns=c_suffix_cols, errors="ignore")

    # Reordenar: colunas originais dos parcels primeiro, depois as do combined
    parcel_cols_present = [c for c in parcels_original_cols if c in merged.columns]
    combined_cols_added = [
        c for c in merged.columns
        if c not in parcel_cols_present
        and c not in ("_idx",)
    ]
    final_order = parcel_cols_present + combined_cols_added
    merged = merged[final_order]

    # Salvar
    merged.to_csv(OUT_ENRICHED, index=False, encoding="utf-8-sig")
    log(f"\n  💾 Salvo: {OUT_ENRICHED}", report_fp)

    # Resumo de colunas
    log(f"\n  Total de colunas no arquivo final: {len(merged.columns)}", report_fp)
    log("  Colunas dos parcels (originais):", report_fp)
    for c in parcel_cols_present:
        log(f"    [parcels]  {c}", report_fp)
    log("  Colunas adicionadas do combined:", report_fp)
    for c in combined_cols_added:
        log(f"    [combined] {c}", report_fp)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# RELATÓRIO POR ESTADO
# ─────────────────────────────────────────────────────────────────────────────

def state_report(merged: pd.DataFrame, report_fp):
    log("\n" + "=" * 62, report_fp)
    log("  RESUMO POR ESTADO", report_fp)
    log("=" * 62, report_fp)

    # Detecta se o merge funcionou verificando se 'County Code' foi preenchido
    match_col = "County Code" if "County Code" in merged.columns else merged.columns[-1]

    summary = (
        merged.groupby("State")
        .agg(
            total=("Parcel Number", "count"),
            com_match=(match_col, lambda x: (x.notna() & (x != "")).sum()),
        )
        .assign(pct_match=lambda d: (d["com_match"] / d["total"] * 100).round(1))
        .sort_values("State")
    )

    log(f"{'Estado':<10} {'Total':>10} {'Com Match':>12} {'%':>8}", report_fp)
    log("-" * 44, report_fp)
    for state, row in summary.iterrows():
        status = "✅" if row["pct_match"] == 100 else ("⚠️ " if row["pct_match"] > 80 else "❌")
        log(f"{status} {state:<8} {int(row['total']):>10,} {int(row['com_match']):>12,} {row['pct_match']:>7.1f}%", report_fp)

    total_all    = int(summary["total"].sum())
    matched_all  = int(summary["com_match"].sum())
    pct_all      = matched_all / total_all * 100 if total_all > 0 else 0
    log("-" * 44, report_fp)
    log(f"  {'TOTAL':<8} {total_all:>10,} {matched_all:>12,} {pct_all:>7.1f}%", report_fp)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    with open(REPORT_FILE, "w", encoding="utf-8") as report_fp:

        log("=" * 62, report_fp)
        log("  MERGE AUCTION DATA — ParcelFair Pipeline", report_fp)
        log("=" * 62, report_fp)

        # ── ETAPA 1: Parcels ──────────────────────────────────────────────
        log("\n[1/4] Carregando CSVs de parcels...", report_fp)
        df_parcels = load_all_parcels(PARCELS_DIR, report_fp)
        parcels_original_cols = [
            c for c in df_parcels.columns if not c.startswith("_")
        ]
        log(f"\n  ✅ Total: {len(df_parcels):,} parcels de {df_parcels['_source_file'].nunique()} estados", report_fp)

        # Salvar parcels combinados (sem enriquecimento)
        df_parcels.drop(columns=[c for c in df_parcels.columns if c.startswith("_")]) \
                  .to_csv(OUT_ALL, index=False, encoding="utf-8-sig")
        log(f"  💾 Salvo: {OUT_ALL}", report_fp)

        # ── ETAPA 2: Combined ─────────────────────────────────────────────
        log("\n[2/4] Carregando combined_auctions_data.csv...", report_fp)
        df_combined = prepare_combined(COMBINED_FILE, report_fp)
        log(f"  ✅ Pronto para o join: {len(df_combined):,} registros únicos", report_fp)

        # ── ETAPA 3: Join progressivo ─────────────────────────────────────
        log("\n[3/4] Executando merge (estratégia progressiva)...", report_fp)
        merged = left_join_progressive(df_parcels, df_combined, report_fp)
        log(f"\n  ✅ Total após merge: {len(merged):,} (sem explosão de linhas)", report_fp)

        # ── ETAPA 4: Organizar e salvar ───────────────────────────────────
        log("\n[4/4] Organizando colunas e salvando...", report_fp)
        merged_final = organize_and_save(merged, parcels_original_cols, report_fp)

        # ── Relatório por estado ──────────────────────────────────────────
        state_report(merged_final, report_fp)

        log("\n" + "=" * 62, report_fp)
        log("  ✅ MERGE CONCLUÍDO COM SUCESSO", report_fp)
        log("=" * 62, report_fp)

    print(f"\n📄 Relatório: {REPORT_FILE}")
    print(f"📂 Arquivos gerados:")
    print(f"   {OUT_ALL}")
    print(f"   {OUT_ENRICHED}")


if __name__ == "__main__":
    main()
