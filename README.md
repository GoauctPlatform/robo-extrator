# 🏠 Scraping Parcel Auction Pipeline

Pipeline automatizado para coleta, enriquecimento, unificação e exportação de dados de leilões imobiliários e parcelas (*parcels*) do ParcelFair para PostgreSQL.

---

## 🚀 Funcionalidades

- **Dashboard Web Interativo (`dashboard_server.py`)**: Interface amigável para controle de execução, bloqueio progressivo de fases e visualização de logs em tempo real.
- **Scraping Headless de Parcels (`data_parcel_auct.py`)**: Coleta robusta em segundo plano via Selenium e BeautifulSoup.
- **Download do Calendário de Leilões (`download_auction_calendar.py`)**: Exportação automática por estado com tratamento de downloads sem popups.
- **Unificação & Merge (`combine_auction_csvs.py`, `merge_auction_data.py`)**: Junção de dados com estratégias progressivas de casamento de chaves.
- **Geração Relacional (`generate_postgres_csvs.py`)**: Produz tabelas relacionais idempotentes para importação no PostgreSQL.
- **Limpeza & Auditoria (`organize_and_audit.sh`)**: Versiona os artefatos de cada rodada na pasta `audit/` e reseta os checkpoints.

---

## 🛠️ Pré-requisitos & Instalação

1. **Google Chrome** instalado.
2. **Python 3.10+** instalado.
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuração de Variáveis de Ambiente

Copie o arquivo de exemplo e preencha suas credenciais:

```bash
cp .env.example .env
```

Edite o `.env`:
```env
PARCELFAIR_EMAIL=seu_email@exemplo.com
PARCELFAIR_PASSWORD=sua_senha_aqui
```

---

## 🖥️ Como Usar

### Opção 1: Pelo Dashboard Web (Recomendado)

Inicie o servidor local:
```bash
python3 dashboard_server.py
```
Acesse no navegador: **`http://localhost:5050`**

### Opção 2: Linha de Comando (Passo a Passo)

1. **Coleta de dados:**
   ```bash
   python3 data_parcel_auct.py
   python3 download_auction_calendar.py
   ```
2. **Combinação e Merge:**
   ```bash
   python3 combine_auction_csvs.py
   python3 merge_auction_data.py
   ```
3. **Geração dos CSVs para PostgreSQL:**
   ```bash
   python3 generate_postgres_csvs.py
   ```
4. **Limpeza e Auditoria:**
   ```bash
   ./organize_and_audit.sh
   ```

---

## 📂 Estrutura do Projeto

```
.
├── dashboard_server.py              # Interface Web em Flask
├── data_parcel_auct.py              # Scraping de parcels
├── download_auction_calendar.py     # Download de calendários de leilão
├── combine_auction_csvs.py          # Concatenação de calendários
├── merge_auction_data.py            # Enriquecimento e merge de dados
├── generate_postgres_csvs.py        # Geração de CSVs para PostgreSQL
├── organize_and_audit.sh            # Script de auditoria e arquivamento
├── requirements.txt                 # Dependências do projeto
├── .env.example                     # Template de variáveis de ambiente
├── .gitignore                       # Proteção de credenciais e datasets grandes
└── Docs/                            # Documentação técnica detalhada
```
