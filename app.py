# Importa a função create_app do pacote app, responsável por criar a aplicação Flask
from app import create_app

# Cria uma instância da aplicação Flask usando a factory function
app = create_app()

# Verifica se o arquivo está sendo executado diretamente
if __name__ == "__main__":
    # Importa e executa a função para inicializar o banco de dados (produção)
    from app.models import inicializar_banco
    inicializar_banco()
    # Cria tabelas de custo se não existirem
    from database.connection import criar_tabelas_custo
    criar_tabelas_custo()
    
    # Usa Waitress para produção ou Flask dev server para desenvolvimento
    import os
    from app.config import SERVER_PORT
    if os.getenv('FLASK_ENV') == 'production' or os.getenv('USE_WAITRESS', '').lower() == 'true':
        from waitress import serve
        print(f"Iniciando servidor com Waitress na porta {SERVER_PORT}...")
        serve(app, host="0.0.0.0", port=SERVER_PORT)
    else:
        # Modo desenvolvimento com Flask dev server
        app.run(host="0.0.0.0", port=SERVER_PORT, debug=True)
