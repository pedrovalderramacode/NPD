"""
Módulo de conexão com o banco de dados SQLite (compartilhado com produção e custos)
"""
import sqlite3
import os

# Caminho do banco - mesmo arquivo usado pela produção (NPD)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados_producao.db')


def get_db():
    """
    Retorna uma conexão com o banco de dados SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas_custo():
    """
    Cria as tabelas de custo (custo_papel, custo_operacional) se não existirem.
    """
    conn = None
    try:
        conn = get_db()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS custo_papel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                papel TEXT NOT NULL,
                custo_kg REAL NOT NULL,
                data_registro TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS custo_operacional (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                despesa TEXT NOT NULL,
                custo_unidade REAL NOT NULL,
                data_registro TEXT NOT NULL
            )
        """)

        conn.commit()
    except Exception as e:
        print(f"Aviso na criação de tabelas de custo: {e}")
    finally:
        if conn:
            conn.close()
