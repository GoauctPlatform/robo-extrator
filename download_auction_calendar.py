import time
import os
import json
import glob
import shutil

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

from dotenv import load_dotenv

load_dotenv()

# ===================================================
# CONFIG
# ===================================================

EMAIL = os.getenv("PARCELFAIR_EMAIL", "")
PASS  = os.getenv("PARCELFAIR_PASSWORD", "")

OUTPUT_DIR      = os.path.abspath("parcelfair_csv_auctions")
CHECKPOINT_FILE = "checkpoint_calendar_download.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Estados presentes no dropdown da página
STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","DC","WV","WI","WY"
]

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
# DRIVER — headless + auto-download sem popup de SO
# ===================================================

def build_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Preferências de download — evita popup "Deseja salvar?" (macOS e Windows)
    prefs = {
        "download.default_directory": OUTPUT_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
        "safebrowsing.disable_download_protection": True,
        "profile.default_content_settings.popups": 0,
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=chrome_options)

    # CDP: força permissão de download em modo headless
    driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": OUTPUT_DIR},
    )

    return driver

# ===================================================
# AGUARDA DOWNLOAD CONCLUIR
# ===================================================

def snapshot_downloads():
    """Retorna o conjunto de arquivos já existentes antes do export."""
    return set(
        glob.glob(os.path.join(OUTPUT_DIR, "*.csv"))
        + glob.glob(os.path.join(OUTPUT_DIR, "*.xlsx"))
        + glob.glob(os.path.join(OUTPUT_DIR, "*.xls"))
    )

def wait_for_new_download(before: set, timeout: int = 90) -> str | None:
    """
    Aguarda um arquivo NOVO aparecer na pasta e terminar de baixar.
    Compara com o snapshot 'before' tirado antes do clique em Export.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        in_progress = glob.glob(os.path.join(OUTPUT_DIR, "*.crdownload"))
        current = set(
            glob.glob(os.path.join(OUTPUT_DIR, "*.csv"))
            + glob.glob(os.path.join(OUTPUT_DIR, "*.xlsx"))
            + glob.glob(os.path.join(OUTPUT_DIR, "*.xls"))
        )
        new_files = current - before

        if new_files and not in_progress:
            return max(new_files, key=os.path.getmtime)

        time.sleep(1)

    return None

# ===================================================
# LOGIN
# ===================================================

def login(driver, wait):
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
# FECHA ABAS EXTRAS — volta para a janela principal
# ===================================================

def close_extra_tabs(driver, main_handle: str):
    """Fecha qualquer aba/janela extra que tenha aberto, volta para a principal."""
    for handle in driver.window_handles:
        if handle != main_handle:
            try:
                driver.switch_to.window(handle)
                driver.close()
            except Exception:
                pass
    driver.switch_to.window(main_handle)

# ===================================================
# EXPORTA UM ESTADO
# ===================================================

def export_state(driver, wait, main_handle: str, state: str) -> bool:
    """
    Navega para o calendário do estado, seleciona no dropdown e clica em Export.
    Trata abas extras que o Export possa abrir.
    Retorna True se o download foi detectado com sucesso.
    """
    url = f"https://parcelfair.com/Auction/Calendar?state={state}&status=All"
    driver.get(url)

    # Espera a página carregar completamente (leva ~5s conforme observado)
    wait.until(EC.presence_of_element_located((By.ID, "state")))
    time.sleep(6)  # margem extra para o JS da página terminar de renderizar

    # Garante que a janela principal ainda é a ativa
    driver.switch_to.window(main_handle)

    # Seleciona o estado no dropdown (dispara filterResults())
    select_el = Select(driver.find_element(By.ID, "state"))
    select_el.select_by_value(state)
    time.sleep(3)  # aguarda filterResults() re-renderizar a tabela

    # Tira snapshot dos arquivos existentes ANTES do clique
    before = snapshot_downloads()

    # Clica no botão Export via JS (mais confiável que click() direto)
    export_btn = wait.until(EC.presence_of_element_located((By.ID, "exportButton")))
    driver.execute_script("arguments[0].click();", export_btn)

    # Pequena pausa para o browser processar o evento de clique
    time.sleep(2)

    # Fecha abas extras que tenham aberto (o Export pode abrir nova aba/janela)
    close_extra_tabs(driver, main_handle)

    print(f"   📥 Aguardando download para {state}...")
    downloaded_file = wait_for_new_download(before, timeout=90)

    if downloaded_file:
        # Mantém o nome original do arquivo, sem renomear
        print(f"   ✅ Arquivo salvo: {os.path.basename(downloaded_file)}")
        return True
    else:
        print(f"   ⚠️  Timeout: nenhum arquivo baixado para {state}")
        return False

# ===================================================
# LOOP PRINCIPAL
# ===================================================

checkpoint  = load_checkpoint()
done_states = checkpoint["done_states"]

driver      = build_driver()
wait        = WebDriverWait(driver, 30)
main_handle = driver.current_window_handle  # guarda a janela principal

try:
    login(driver, wait)
    main_handle = driver.current_window_handle  # atualiza handle pós-login

    for state in STATES:
        if state in done_states:
            print(f"⏩ Pulando {state} (já feito)")
            continue

        print(f"\n🚀 Exportando calendário: {state}")

        try:
            success = export_state(driver, wait, main_handle, state)
            if success:
                done_states.append(state)
                checkpoint["done_states"] = done_states
                save_checkpoint(checkpoint)
        except Exception as e:
            print(f"   ⚠️  Erro no estado {state}: {e}")
            # Tenta recuperar a janela principal antes de continuar
            try:
                close_extra_tabs(driver, main_handle)
            except Exception:
                pass
            continue

finally:
    driver.quit()
    print(f"\n🎉 Download finalizado! Arquivos em: {OUTPUT_DIR}")
