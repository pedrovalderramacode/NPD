# Configura a localidade para datas em português do Brasil
import locale
from flask import Flask

locale.setlocale(locale.LC_TIME, 'pt_BR.utf8' if locale.getpreferredencoding() != 'cp1252' else 'Portuguese_Brazil.1252')

# Função factory para criar a aplicação Flask
def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    # Chave secreta para sessões e segurança
    app.secret_key = 'producao_secret_key_muito_segura_e_final'

    # Importa e registra o blueprint principal (produção)
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # Importa e registra os blueprints de custo
    from .custo.routes.custos_papel import bp as custos_papel_bp
    from .custo.routes.custos_operacionais import bp as custos_operacionais_bp
    from .custo.routes.relatorio import bp as relatorio_bp
    app.register_blueprint(custos_papel_bp)
    app.register_blueprint(custos_operacionais_bp)
    app.register_blueprint(relatorio_bp)

    # Retorna a aplicação pronta para uso
    return app
