# 🚀 Guia Prático: Usando o Sistema de Reconciliação

## ⚡ TL;DR (Versão Rápida)

```bash
# Opção 1: Pipeline completo (recomendado)
./pipeline_complete.sh

# Opção 2: Passo a passo
python3 generate_postgres_csvs.py
python3 reconcile_postgres_csvs.py
```

Pronto! Seus arquivos CSV estão prontos para PostgreSQL com IDs mantidos ✅

---

## 📚 Entendendo Seu Dilema (Resolvido!)

### Antes (O Problema)

Ao executar `generate_postgres_csvs.py` novamente:

```
Versão 1 (primeira execução):
- Property: b0a13be2-395b-439a-a3e7-11471ae7853a ← UUID gerado
- Auction ID: 1 ← ID sequencial

Versão 2 (segunda execução):
- Property: 8c7f3a2b-1234-5678-abcd-ef9999999999 ← ⚠️ UUID DIFERENTE!
- Auction ID: 1 ← OK (mesma posição)
```

**Resultado**: Integridade referencial quebrada no banco de dados! 💥

### Depois (A Solução)

Com `reconcile_postgres_csvs.py`:

```
Versão 1 (primeira execução):
- Property: b0a13be2-395b-439a-a3e7-11471ae7853a 
- Auction ID: 1

Versão 2 (segunda execução + reconciliação):
- Property: b0a13be2-395b-439a-a3e7-11471ae7853a ← ✅ ID MANTIDO!
- Auction ID: 1 ← ✅ ID MANTIDO!
```

**Resultado**: Dados podem ser adicionados/atualizados sem quebrar o banco! ✨

---

## 🔧 Como Funciona Tecnicamente

### 1️⃣ Identificação Única

O script identifica registros **sem** depender de IDs (que podem mudar):

**Leilão** = `(nome, estado, data)`
```python
key = ("Jefferson-Birmingham ADOR EBuy Auction", "AL", "2026-03-02")
# Se esse mesmo leilão aparecer novamente → mesmo ID
```

**Propriedade** = `(parcel_id, county, state)`
```python
key = ("01 16 00 17 0 000 009.000", "Jefferson-Birmingham", "AL")
# Se essa mesma propriedade aparecer novamente → mesmo ID
```

### 2️⃣ Mapeamento de IDs

Quando o script executa:

```
LEGACY (Baseline):
├─ Leilão: "Jefferson-Birmingham..." → ID 1
└─ Propriedade: "01 16 00 17 0 000 009.000" → UUID b0a13be2...

NOVO (Gerado):
├─ Leilão: "Jefferson-Birmingham..." → ID 150 (ID gerado)
└─ Propriedade: "01 16 00 17 0 000 009.000" → UUID f7ac9e12...

RECONCILIADO (Resultado):
├─ Leilão: "Jefferson-Birmingham..." → ID 1 ✅ (mantém antigo)
└─ Propriedade: "01 16 00 17 0 000 009.000" → UUID b0a13be2... ✅ (mantém antigo)
```

### 3️⃣ Novos Registros

Registros completamente novos recebem IDs novos:

```
NOVO:
├─ Leilão novo: "Phoenix Real Estate Auction" → ID 151 (novo)
│  └─ Reconciliado: "Phoenix Real Estate Auction" → ID 2606 ✅ (sequencial após máximo)
│
└─ Propriedade nova: "23 45 67 89..." → UUID c1d2e3f4...
   └─ Reconciliado: "23 45 67 89..." → UUID c1d2e3f4... ✅ (mantém novo)
```

---

## 📊 Dados do Exemplo Real

Do seu último run:

| Entidade | Legacy | Novo | Mantido | Novo |
|----------|--------|------|---------|------|
| **Leilões** | 2.605 | 2.281 | 2.041 | 240 |
| **Propriedades** | 150.522 | 136.252 | 124.343 | 11.909 |
| **Histórico** | 150.522 | 136.252 | - | - |

**Interpretação**:
- ✅ 2.041 leilões mantêm IDs antigos (confiança no banco)
- ✅ 240 leilões novos recebem IDs 2.606-2.845
- ✅ 124.343 propriedades mantêm UUIDs antigos
- ✅ 11.909 propriedades novas recebem UUIDs novos
- ✅ Todo histórico é remapeado corretamente

---

## 📋 Passo a Passo Completo

### Cenário: Você adicionou novos dados e quer gerar CSVs para PostgreSQL

```bash
# 1. Certifique-se de estar no diretório correto
cd /Users/gustavo/Documents/dev/projects/webScraping/scraping_parcelfair/pipeline/scraping_parcel_auction

# 2. Execute o pipeline completo (recomendado)
./pipeline_complete.sh

# OU faça manualmente:

# 2a. Gerar novos arquivos a partir dos dados enriquecidos
python3 generate_postgres_csvs.py
# Gera:
#   - postgres_auction_events.csv (novo)
#   - postgres_property_details.csv (novo)
#   - postgres_property_auction_history.csv (novo)

# 2b. Reconciliar com baseline
python3 reconcile_postgres_csvs.py
# Sobrescreve os 3 arquivos anteriores com versões reconciliadas

# 3. Valide (opcional)
ls -lh postgres_*.csv
wc -l postgres_*.csv
```

### Resultado Esperado

```
✓ postgres_auction_events.csv (830 KB)
✓ postgres_property_details.csv (25 MB)
✓ postgres_property_auction_history.csv (7.9 MB)

IDs mantidos para registros existentes ✅
IDs novos para novos registros ✅
Histórico remapeado corretamente ✅
```

---

## 🔐 Garantias do Sistema

✅ **Determinístico**: Mesmos dados sempre recebem mesmos IDs  
✅ **Idempotente**: Executar 2x = executar 1x (não piora)  
✅ **Sem perda de dados**: Tudo fica salvo em `06.04.26_auction_parcels_csvs/`  
✅ **Integridade referencial**: Histórico sempre vinculado corretamente  
✅ **Escalável**: Funciona com qualquer número de registros  

---

## 🎯 Seu Próximo Workflow

```
1. Adicionar novos dados (web scraping, etc)
   ↓
2. Executar seu processamento
   ↓
3. ./pipeline_complete.sh
   ↓
4. Upload para PostgreSQL
   ↓
5. Análise/queries no banco
```

**Repetir conforme necessário** - os IDs sempre se manterão estáveis! 🚀

---

## ❓ Perguntas Comuns

### P: E se eu adicionar muitos dados novos de uma vez?

R: Sem problema! Novos registros recebem novos IDs sequenciais. Apenas certifique-se de que:
- O diretório `06.04.26_auction_parcels_csvs/` está atualizado (versão mais recente que você quer manter)

### P: Preciso fazer backup antes?

R: Sim, por segurança:
```bash
cp -r 06.04.26_auction_parcels_csvs 06.04.26_auction_parcels_csvs.backup
```

### P: E se houver conflito de dados?

R: O script de reconciliação **sempre prefere os dados novos** quando há atualização:
```python
# Se a propriedade já existe e o availability_status mudou:
OLD: availability_status = "available"
NEW: availability_status = "unavailable"
RESULT: availability_status = "unavailable" ← Novo valor
```

### P: Posso excluir dados?

R: O script não exclui. Se uma propriedade desaparecer do novo arquivo, ela ainda estará no antigo. Para "excluir" logicamente, use flags no banco (ex: `is_active = False`).

---

## 🚨 Troubleshooting

### Erro: `FileNotFoundError: No such file or directory`

```
Solução: Verifique se o diretório 06.04.26_auction_parcels_csvs/ existe
         Se não existir, execute first-time setup:
         mkdir -p 06.04.26_auction_parcels_csvs
         cp postgres_*.csv 06.04.26_auction_parcels_csvs/
```

### Erro: `KeyError: 'name'`

```
Solução: Verifica se a coluna existe em ambos os CSVs
         Compare cabeçalhos: head -1 postgres_auction_events.csv
```

### IDs diferentes do esperado

```
Solução NORMAL: Na primeira reconciliação, IDs podem variar se muitos 
                registros foram modificados
Verificar: Compare IDs no arquivo novo com o legacy antes de reconciliar
```

---

## 📞 Resumo da Solução

**Seu dilema**: IDs mudam a cada execução ❌  
**Nossa solução**: Reconciliação com identificação única ✅  
**Seu ganho**: Banco de dados estável e escalável 🎉  

Agora você pode:
- ✅ Adicionar dados novos regularmente
- ✅ Manter integridade referencial
- ✅ Escalar para milhões de registros
- ✅ Automatizar o workflow completo

**Sucesso!** 🚀
