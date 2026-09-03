# 🏠 Scraping Parcel Auction Pipeline

Pipeline automatizado para coleta, enriquecimento, unificação e exportação de dados de leilões imobiliários e parcelas (*parcels*) do ParcelFair para PostgreSQL.

---

## 🚀 Funcionalidades

- **Dashboard Web Interativo (`dashboard_server.py`)**: Interface amigável para controle de execução, bloqueio progressivo de fases e visualização de logs em tempo real.
- **Scraping Headless de Parcels (`data_parcel_auct.py`)**: Coleta robusta em segundo plano via Selenium e BeautifulSoup.
- **Download do Calendário de Leilões (`download_auction_calendar.py`)**: Exportação automática por estado com tratamento de downloads sem popups.
- **Unificação & Merge (`combine_auction_csvs.py`, `merge_auction_data.py`)**: Junção de dados com estratégias progressivas de casamento de chaves.
- **Geração Relacional (`generate_postgres_csvs.py`)**: Produz tabelas relacionais idempotentes para importação no PostgreSQL.
- **Divisão & Envio (`split_csvs.py`, `send_to_platform.py`)**: Particiona os CSVs em 4 fatias e transfere para o backend da Goauct-Platform.
- **Importação Remota Paralela (`remote_import_runner.py`)**: Orquestração multi-thread (4 partes paralelas) de importação para o banco de dados remoto da Goauct-Platform, respeitando a sequência relacional (Propriedades → Leilões → Vínculos/Histórico).
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

### Opção 1: Atalho na Área de Trabalho (Mais Fácil)
Dê um duplo clique no ícone **Parcel Auction Dashboard** na sua Área de Trabalho (Desktop). O terminal iniciará o servidor e abrirá automaticamente o navegador em `http://localhost:5050`.

> **Nota**: Para recriar o atalho no Desktop a qualquer momento, execute:
> ```bash
> python create_desktop_shortcut.py
> ```

### Opção 2: Pelo Script Batch / Linha de Comando
Execute o inicializador:
```cmd
iniciar_dashboard.bat
```
Ou inicie o servidor Python diretamente:
```bash
python dashboard_server.py
```
Acesse no navegador: **`http://localhost:5050`**

### Opção 3: Linha de Comando (Passo a Passo)

1. **Coleta de dados:**
   ```bash
   python data_parcel_auct.py
   python download_auction_calendar.py
   ```
2. **Combinação e Merge:**
   ```bash
   python combine_auction_csvs.py
   python merge_auction_data.py
   ```
3. **Geração dos CSVs para PostgreSQL:**
   ```bash
   python generate_postgres_csvs.py
   ```
4. **Divisão e Envio para Goauct-Platform:**
   ```bash
   python split_csvs.py
   python send_to_platform.py [--overwrite]
   ```
5. **Importação Remota no Banco (Goauct-Platform):**
   ```bash
   # Executa as 3 etapas na ordem relacional correta (4 partes em paralelo cada):
   python remote_import_runner.py --stage all

   # Ou etapa por etapa individualmente:
   python remote_import_runner.py --stage properties
   python remote_import_runner.py --stage auctions
   python remote_import_runner.py --stage history
   ```
6. **Limpeza e Auditoria:**
   ```bash
   bash organize_and_audit.sh
   ```

---

## 📂 Estrutura do Projeto

```
.
├── dashboard_server.py              # Interface Web em Flask
├── iniciar_dashboard.bat            # Inicializador 1-clique (inicia servidor + abre navegador)
├── create_desktop_shortcut.py       # Gerador do atalho na Área de Trabalho
├── data_parcel_auct.py              # Scraping de parcels
├── download_auction_calendar.py     # Download de calendários de leilão
├── combine_auction_csvs.py          # Concatenação de calendários
├── merge_auction_data.py            # Enriquecimento e merge de dados
├── generate_postgres_csvs.py        # Geração de CSVs para PostgreSQL
├── split_csvs.py                    # Divisão dos CSVs em 4 partes
├── send_to_platform.py              # Exportação para Goauct-Platform (com controle de sobrescrita)
├── remote_import_runner.py          # Importação remota paralela (Goauct-Platform)
├── organize_and_audit.sh            # Script de auditoria e arquivamento
├── requirements.txt                 # Dependências do projeto
├── .env.example                     # Template de variáveis de ambiente
├── .gitignore                       # Proteção de credenciais e datasets grandes
└── Docs/                            # Documentação técnica detalhada
```

