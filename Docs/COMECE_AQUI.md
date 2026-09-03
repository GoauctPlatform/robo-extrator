# ⚡ Começar Agora - Guia de 5 Minutos

## 1️⃣ Verifique se tem tudo

```bash
cd /Users/gustavo/Documents/dev/projects/webScraping/scraping_parcelfair/pipeline/scraping_parcel_auction

# Verifique se os arquivos existem:
ls -la 06.04.26_auction_parcels_csvs/
ls -la reconcile_postgres_csvs.py
ls -la pipeline_complete.sh
```

Se tudo existe, prossiga para o próximo passo ✅

## 2️⃣ Execute o pipeline

```bash
# Opção A: Pipeline Completo (Recomendado - tudo automático)
./pipeline_complete.sh

# Opção B: Manual (Se quer fazer passo a passo)
python3 generate_postgres_csvs.py
python3 reconcile_postgres_csvs.py
```

Aguarde 20-30 segundos ⏳

## 3️⃣ Verifique o resultado

```bash
# Seus arquivos estão prontos?
ls -lh postgres_*.csv

# Quantos registros?
wc -l postgres_*.csv

# Estrutura OK?
head -1 postgres_property_details.csv
```

## 4️⃣ Pronto! 🎉

Seus arquivos CSV estão reconciliados e prontos para:
- ✅ Upload para PostgreSQL
- ✅ Análise de dados
- ✅ Distribuição

---

## 🚨 Algo deu errado?

### Erro: "File not found"
```bash
# Verifique se o diretório baseline existe
ls -la 06.04.26_auction_parcels_csvs/

# Se não existir, crie:
mkdir -p 06.04.26_auction_parcels_csvs
cp postgres_*.csv 06.04.26_auction_parcels_csvs/
```

### Erro: "ModuleNotFoundError: pandas"
```bash
pip install pandas
```

### IDs completamente diferentes
Isto é OK! Na primeira reconciliação, IDs podem mudar se os dados foram significativamente modificados. Após a primeira execução, ficam estáveis.

---

## 📚 Quer saber mais?

- **Como funciona?** → Leia [GUIA_PRATICO.md](GUIA_PRATICO.md)
- **Explicação técnica?** → Leia [RECONCILE_README.md](RECONCILE_README.md)
- **Deep dive?** → Leia [ARQUITETURA_TECNICA.md](ARQUITETURA_TECNICA.md)
- **Índice de tudo?** → Leia [INDEX.md](INDEX.md)

---

## ✅ Checklist

- [ ] Diretório 06.04.26_auction_parcels_csvs/ existe?
- [ ] Arquivos antigos .csv estão dentro?
- [ ] Executou ./pipeline_complete.sh?
- [ ] Arquivos novos aparecem na raiz?
- [ ] Nenhum erro foi exibido?

**Se tudo OK**: Você conseguiu! 🎊

---

## 🔄 Fluxo Repetitivo (Como usar sempre)

```
1. Adicionar dados novos (web scraping, etc)
                ↓
2. Executar processamento
                ↓
3. ./pipeline_complete.sh
                ↓
4. postgres_*.csv prontos!
                ↓
5. Upload para PostgreSQL
                ↓
6. Repetir conforme necessário
```

IDs sempre estarão estáveis! ✨

---

**Pronto para começar?**

```bash
./pipeline_complete.sh
```

Good luck! 🚀
