# NPD - Sistema Integrado de Produção e Custos

Sistema unificado para controle de produção industrial e cálculo de custos, desenvolvido em Flask. Inclui lançamento de produção, relatórios, análises e gestão de custos (papel e operacionais).

## Estrutura do Projeto

```
.
├── app.py                # Ponto de entrada da aplicação
├── app/                  # Módulos do backend
│   ├── __init__.py       # Inicialização do app Flask
│   ├── routes.py         # Rotas de produção
│   ├── models.py         # Banco de dados e inicialização
│   ├── business.py       # Lógica de negócio
│   ├── charts.py         # Geração de gráficos
│   ├── config.py         # Constantes e configurações
│   └── custo/            # Módulo de custos
│       ├── routes/       # Rotas (relatório, custo papel, custos operacionais)
│       ├── services/     # Lógica de negócio de custos
│       └── utils/        # Formatadores
├── database/             # Conexão e tabelas de custo
├── templates/            # Templates HTML (Jinja2)
│   ├── base.html         # Layout unificado com navegação
│   ├── index.html
│   ├── historico.html
│   ├── custos_papel/
│   ├── custos_operacionais/
│   └── relatorio/
├── static/
├── dados_producao.db     # Banco de dados SQLite (compartilhado)
└── backup/
```

## Instalação

1. **Clone o repositório:**
   ```bash
   git clone <seu-repo>
   cd <seu-repo>
   ```

2. **Crie um ambiente virtual (opcional, mas recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate    # Windows
   ```

3. **Instale as dependências:**
   ```bash
   pip install flask pandas matplotlib numpy waitress xlsxwriter
   ```

4. **Configure o caminho do banco de dados:**
   - Por padrão, o caminho está em `app/config.py` na variável `DB_NAME`.
   - Você pode sobrescrever via variável de ambiente `DB_NAME`.

## Execução

1. **Inicialize o banco de dados (apenas na primeira vez):**
   - O banco será criado automaticamente ao rodar o app.

2. **Execute a aplicação:**
   ```bash
   python app.py
   ```
   - O servidor estará disponível em [http://localhost:8080](http://localhost:8080)

3. **Para produção:**
   - O projeto já suporta Waitress (WSGI). Para rodar em produção:
   ```bash
   python app.py
   ```
   - Ou use um servidor WSGI de sua preferência.

## Funcionalidades

### Produção
- **Lançamento:** Cadastro de dados de produção com cálculo automático de métricas.
- **Histórico:** Filtros avançados, ordenação, exportação para Excel.
- **OF-Refugo:** Relatório simplificado de OFs com refugos.
- **Comparação Quantidade:** Comparação entre comanda, impressora e SOS.
- **Comparativo Mensal:** Métricas mês a mês.
- **Análise:** Tabelas de resumo por máquina, operador, formato e papel.

### Custos
- **Relatório de Custo OFs:** Relatório de custos por OF com filtro por período.
- **Custo Papel:** Cadastro de custos por kg de papel.
- **Custos Adicionais:** Configuração de despesas (TINTA, COLA, ALÇA, etc.).

## Dicas e Customização
- Para adicionar operadores, máquinas ou formatos, edite `app/config.py`.
- Para customizar estilos, edite os arquivos em `static/css/`.
- Para adicionar novas rotas ou relatórios, utilize o padrão de blueprints em `app/routes.py`.

## Licença

Este projeto é privado e de uso interno. 