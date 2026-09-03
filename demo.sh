#!/bin/bash
# Script de Demonstração - Sistema Idempotente

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  DEMONSTRAÇÃO - Sistema Idempotente"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

BASE_DIR="/Users/gustavo/Documents/dev/projects/webScraping/scraping_parcelfair/pipeline/scraping_parcel_auction"

# Função para exibir menu
show_menu() {
    echo ""
    echo "Escolha uma opção:"
    echo "  1) Executar generate_postgres_csvs.py"
    echo "  2) Validar Idempotência (2x execuções)"
    echo "  3) Ver documentação"
    echo "  4) Ver status de backups"
    echo "  5) Sair"
    echo ""
    read -p "Opção: " choice
}

# Função para executar generator
run_generator() {
    echo ""
    echo "Executando generate_postgres_csvs.py..."
    cd "$BASE_DIR"
    python3 generate_postgres_csvs.py
}

# Função para validar idempotência
validate_idempotence() {
    echo ""
    echo "Validando idempotência..."
    cd "$BASE_DIR"
    python3 validate_idempotence.py
}

# Função para ver documentação
show_documentation() {
    echo ""
    echo "Documentação disponível:"
    echo ""
    echo "1) GUIA_RAPIDO.md - Como usar"
    echo "2) PLANO_IMPLEMENTACAO_FINAL.md - Detalhes técnicos"
    echo "3) RELATORIO_FINAL_IDEMPOTENCIA.md - Resultados dos testes"
    echo "4) RESUMO_EXECUTIVO.txt - Resumo visual"
    echo ""
    read -p "Qual deseja abrir? (1-4): " doc_choice
    
    case $doc_choice in
        1) cat "$BASE_DIR/GUIA_RAPIDO.md" ;;
        2) cat "$BASE_DIR/PLANO_IMPLEMENTACAO_FINAL.md" ;;
        3) cat "$BASE_DIR/RELATORIO_FINAL_IDEMPOTENCIA.md" ;;
        4) cat "$BASE_DIR/RESUMO_EXECUTIVO.txt" ;;
        *) echo "Opção inválida" ;;
    esac
}

# Função para ver backups
show_backups() {
    echo ""
    echo "Estado de backups:"
    echo ""
    ls -lh "$BASE_DIR/previous_exports"/*/postgres_property_details.csv
    echo ""
    echo "Timestamps encontrados:"
    ls -d "$BASE_DIR/previous_exports"/*/ | xargs -n1 basename
}

# Loop principal
while true; do
    show_menu
    
    case $choice in
        1) run_generator ;;
        2) validate_idempotence ;;
        3) show_documentation ;;
        4) show_backups ;;
        5) 
            echo "Saindo..."
            exit 0
            ;;
        *) 
            echo "Opção inválida!"
            ;;
    esac
done
