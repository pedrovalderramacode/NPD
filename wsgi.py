"""
Arquivo WSGI para produção usando Waitress
"""
from app import create_app
from app.models import inicializar_banco

# Inicializa o banco de dados
inicializar_banco()

# Cria a aplicação Flask
application = create_app()

if __name__ == "__main__":
    # Para desenvolvimento, pode rodar diretamente
    from waitress import serve
    from app.config import SERVER_PORT
    serve(application, host="0.0.0.0", port=SERVER_PORT)

