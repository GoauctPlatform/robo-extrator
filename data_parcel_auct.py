import time
import os
import json
import pandas as pd
import csv
from urllib.parse import urljoin, parse_qs, urlparse
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

from dotenv import load_dotenv

load_dotenv()

# ===================================================
# CONFIG
# ===================================================

OUTPUT_DIR = "parcelfair_auction_parcels_csvs"
CHECKPOINT_FILE = "checkpoint_auction_parcels.json"

EMAIL = os.getenv("PARCELFAIR_EMAIL", "")
PASS  = os.getenv("PARCELFAIR_PASSWORD", "")

STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","DC","WV","WI","WY"
]

# Headers originais + novas colunas de contexto do leilão
HEADERS = [
    "Parcel Number","C/S#","PIN","Name","County","State",
    "Availability","Sale Year","Amount Due","Acres",
    "Total Value","Land","Building","Parcel Type",
    "Status","Address","Next Auction","Occupancy"
]
EXTRA_HEADERS = ["Auction Name", "Inventory Type", "Auction Date"]
FULL_HEADERS = HEADERS + EXTRA_HEADERS

# Cria diretório
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ===================================================
# CHECKPOINT
# ===================================================

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"done_states": []}

def save_checkpoint(data):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ===================================================
# DRIVER + WAIT
# ===================================================

from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

checkpoint = load_checkpoint()
done_states = checkpoint["done_states"]

# ===================================================
# LOGIN (exatamente igual ao seu script original)
# ===================================================

print("🔐 Abrindo login...")
driver.get("https://parcelfair.com/Account/Login")

email_input = wait.until(EC.element_to_be_clickable((By.ID, "Email")))
email_input.clear()
email_input.send_keys(EMAIL)

pass_input = wait.until(EC.element_to_be_clickable((By.ID, "Password")))
pass_input.clear()
pass_input.send_keys(PASS)
pass_input.send_keys(Keys.ENTER)

wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Log off")))
print("✅ Login realizado com sucesso")

# ===================================================
# FUNÇÃO PARA EXTRAIR AUCTIONS DO CALENDÁRIO
# ===================================================

def extract_auctions_from_calendar(driver, state):
    # Expande todos os painéis colapsados (importante!)
    try:
        collapse_links = driver.find_elements(By.CSS_SELECTOR, 'a[data-toggle="collapse"]')
        for link in collapse_links:
            if "collapsed" in (link.get_attribute("class") or ""):
                driver.execute_script("arguments[0].click();", link)
                time.sleep(0.8)
    except:
        pass

    time.sleep(3)  # espera carregamento total dos painéis

    soup = BeautifulSoup(driver.page_source, "html.parser")
    auctions = []

    for panel in soup.find_all("div", class_="panel"):
        # Mês/Ano do painel
        panel_title = panel.find("h4", class_="panel-title")
        month_year = ""
        if panel_title:
            m = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', panel_title.get_text())
            if m: month_year = m.group(0)

        for row in panel.find_all("div", class_="row", style=lambda x: x and "margin-bottom:12px" in x.replace(" ", "")):
            lead = row.find("div", class_="lead")
            day_date = lead.get_text(strip=True) if lead else ""
            auction_date = f"{day_date} {month_year}".strip()

            for auction_div in row.find_all("div", class_="auction"):
                # Nome do leilão
                name_tag = auction_div.find("h5", class_="clickable")
                if not name_tag:
                    name_tag = auction_div.find("h5")
                auction_name = name_tag.get_text(strip=True) if name_tag else "Unknown"

                # InventoryType (ID único do leilão)
                clickable = auction_div.find("div", class_="clickable")
                inventory_type = None
                if clickable and clickable.has_attr("onclick"):
                    onclick = clickable["onclick"]
                    if "openAuctionDetails(" in onclick:
                        try:
                            inventory_type = int(onclick.split("(")[1].split(")")[0])
                        except:
                            pass

                # Link específico "Only list parcels from this auction"
                parcel_list_url = None
                county_code = None
                list_dropdowns = auction_div.find_all("ul", class_="dropdown-menu")
                for list_dropdown in list_dropdowns:
                    for a in list_dropdown.find_all("a", href=True):
                        text = ' '.join(a.get_text(strip=True).split())
                        if "list parcels" in text.lower() and "from this auction" in text.lower():
                            relative_href = a["href"]
                            parcel_list_url = urljoin("https://parcelfair.com/", relative_href)
                            # Extrai countyCode e confirma InventoryType
                            parsed = urlparse(parcel_list_url)
                            params = parse_qs(parsed.query)
                            county_code = params.get("countyCode", [None])[0]
                            if not inventory_type:
                                inventory_type_str = params.get("InventoryType", [None])[0]
                                if inventory_type_str:
                                    inventory_type = int(inventory_type_str)
                            break
                    if parcel_list_url:
                        break

                if parcel_list_url and inventory_type:
                    auctions.append({
                        "auction_name": auction_name,
                        "inventory_type": str(inventory_type),
                        "county_code": county_code,
                        "parcel_list_url": parcel_list_url,
                        "auction_date": auction_date
                    })

    print(f"✅ Encontrados {len(auctions)} leilões no calendário de {state}")
    return auctions

# ===================================================
# FUNÇÃO REUTILIZADA: EXTRAIR PARCELS (exatamente sua lógica original)
# ===================================================

def scrape_parcels_from_url(driver, url):
    driver.get(url)

    # Espera inicial
    wait.until(EC.presence_of_element_located((By.ID, "resultsTable")))

    # Espera estabilização da tabela (mesma lógica robusta do seu script)
    prev_row_count = 0
    max_wait = 120
    wait_interval = 5
    elapsed = 0
    while elapsed < max_wait:
        rows = driver.find_elements(By.CSS_SELECTOR, "#resultsTable tr")
        current_row_count = len(rows)
        if current_row_count == prev_row_count and current_row_count > 1:
            break
        prev_row_count = current_row_count
        time.sleep(wait_interval)
        elapsed += wait_interval

    if current_row_count <= 1:
        return pd.DataFrame(columns=FULL_HEADERS)  # vazio

    # JS de extração (igual ao seu)
    js_extract = r"""
    const table = document.querySelector("#resultsTable");
    const rows = table.querySelectorAll("tr");
    const headers = Array.from(rows[0].querySelectorAll("th")).slice(1).map(th => th.innerText.trim());
    const data = [];
    for (let i = 1; i < rows.length; i++) {
        const cells = rows[i].querySelectorAll("td");
        if (!cells.length) continue;
        const row = Array.from(cells).slice(1).map(td => td.innerText.replace(/\n/g," ").replace(/"/g,'""').trim());
        data.push(row);
    }
    return {headers: headers, data: data};
    """

    extracted = driver.execute_script(js_extract)
    extracted_headers = extracted['headers']
    batch = extracted['data']

    if extracted_headers != HEADERS:
        current_headers = extracted_headers
    else:
        current_headers = HEADERS

    # Adiciona State se necessário (igual ao original)
    state_index = current_headers.index("State") if "State" in current_headers else -1
    if state_index != -1:
        for row in batch:
            if len(row) > state_index and not row[state_index]:
                row[state_index] = driver.current_url.split("state=")[-1].split("&")[0].upper()
    else:
        current_headers.insert(5, "State")
        for row in batch:
            row.insert(5, driver.current_url.split("state=")[-1].split("&")[0].upper() if "state=" in driver.current_url else "")

    df = pd.DataFrame(batch, columns=current_headers)
    return df

# ===================================================
# LOOP PRINCIPAL POR ESTADOS
# ===================================================

for state in STATES:
    if state in done_states:
        print(f"⏩ Pulando {state} (já feito)")
        continue

    try:
        print(f"\n🚀 Processando calendário do estado: {state}")

        calendar_url = f"https://parcelfair.com/Auction/Calendar?state={state}&status=All"
        driver.get(calendar_url)

        auctions = extract_auctions_from_calendar(driver, state)

        if not auctions:
            print(f"⚠️ Nenhum leilão encontrado para {state}. Pulando...")
            done_states.append(state)
            checkpoint["done_states"] = done_states
            save_checkpoint(checkpoint)
            continue

        # CSV de saída para este estado
        output_file = os.path.join(OUTPUT_DIR, f"parcelfair_auction_parcels_{state}.csv")
        first_write = True

        for auction in auctions:
            try:
                print(f"   📦 Scraping parcels do leilão: {auction['auction_name']} (ID {auction['inventory_type']})")

                df_parcels = scrape_parcels_from_url(driver, auction["parcel_list_url"])

                if df_parcels.empty:
                    print(f"      ⚠️ Nenhum parcel encontrado para este leilão")
                    continue

                # Adiciona colunas de contexto do leilão
                df_parcels["Auction Name"] = auction["auction_name"]
                df_parcels["Inventory Type"] = auction["inventory_type"]
                df_parcels["Auction Date"] = auction["auction_date"]

                # Reordena colunas
                df_parcels = df_parcels.reindex(columns=FULL_HEADERS)

                # Salva (primeira vez com header, depois append)
                if first_write:
                    df_parcels.to_csv(output_file, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
                    first_write = False
                else:
                    df_parcels.to_csv(output_file, mode='a', header=False, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')

                print(f"      ✅ {len(df_parcels)} parcels salvos para o leilão")

            except Exception as e_auction:
                print(f"      ⚠️ Erro no leilão {auction['auction_name']}: {e_auction}")
                continue

        # Marca estado como concluído
        done_states.append(state)
        checkpoint["done_states"] = done_states
        save_checkpoint(checkpoint)
        print(f"✅ Estado {state} finalizado → {output_file}")

    except Exception as e:
        print(f"⚠️ Erro geral no estado {state}: {e}")
        continue

# ===================================================
# FINALIZA
# ===================================================

driver.quit()
print("\n🎉 SCRAP FINALIZADO!")
print(f"📂 Todos os CSVs com parcels vinculados aos leilões estão em: {OUTPUT_DIR}")
print("🔗 Agora você pode juntar esses arquivos com o combined_auctions_data.csv usando a coluna 'Inventory Type' ou 'Auction Name' + 'County Code'.")