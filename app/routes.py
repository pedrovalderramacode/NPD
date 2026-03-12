from flask import Blueprint, render_template, request, flash, send_file, redirect, url_for, session, jsonify
from datetime import datetime
import pandas as pd
from io import BytesIO
from .models import get_db_connection, inicializar_banco
from .business import calcular_metricas_producao, get_seconds_from_time
from .config import ALL_OPERADORES, ALL_MAQUINAS, OPERADORES_SOS, OPERADORES_IMPRESSORA, OPERADORES_ROBO
from .charts import *

# Função auxiliar para tratar valores vazios
def safe_get_int(form_data, key, default=0):
    """Retorna um inteiro do formulário ou valor padrão se vazio."""
    value = form_data.get(key, '')
    if value == '' or value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_get_float(form_data, key, default=0.0):
    """Retorna um float do formulário ou valor padrão se vazio."""
    value = form_data.get(key, '')
    if value == '' or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_get_str(form_data, key, default=None):
    """Retorna uma string do formulário ou valor padrão se vazio."""
    value = form_data.get(key, '')
    if value == '' or value is None:
        return default if default is not None else ''
    result = str(value).strip()
    return result if result else (default if default is not None else '')

# Cria o blueprint principal para as rotas da aplicação
main_bp = Blueprint('main', __name__)

# Rota principal: formulário de lançamento de produção
@main_bp.route("/")
def index():
    # Não passa valores padrão - formulário começa vazio para novo lançamento
    return render_template('index.html', page_title="Lançamento de Produção", action_url=url_for('main.lancar'), lancamento=None, operadores_sos=OPERADORES_SOS, operadores_impressora=OPERADORES_IMPRESSORA, operadores_robo=OPERADORES_ROBO)

# Rota para buscar dados por Nº OF (AJAX)
@main_bp.route("/buscar_por_of")
def buscar_por_of():
    """Busca um registro pelo Nº OF e retorna os dados em JSON."""
    num_of = request.args.get('num_of', '')
    if not num_of:
        return jsonify({}), 400
    conn = get_db_connection()
    lancamento = conn.execute("SELECT * FROM producao WHERE num_of = ?", (num_of,)).fetchone()
    conn.close()
    if lancamento:
        return jsonify(dict(lancamento))
    return jsonify({}), 404

# Rota para duplicar um lançamento existente
@main_bp.route("/duplicar/<int:id>")
def duplicar(id):
    conn = get_db_connection()
    lancamento_original = conn.execute("SELECT * FROM producao WHERE id = ?", (id,)).fetchone()
    conn.close()
    if lancamento_original is None:
        flash("Registro original não encontrado.", "warning")
        return redirect(url_for('main.historico'))
    lancamento = dict(lancamento_original)
    lancamento['data'] = datetime.today().strftime('%Y-%m-%d')
    lancamento['id'] = None
    return render_template('index.html', page_title="Duplicar Lançamento", action_url=url_for('main.lancar'), lancamento=lancamento, operadores_sos=OPERADORES_SOS, operadores_impressora=OPERADORES_IMPRESSORA, operadores_robo=OPERADORES_ROBO)

# Rota para lançar um novo registro de produção
@main_bp.route("/lancar", methods=["POST"])
def lancar():
    try:
        # Salva últimas seleções na sessão
        session['last_operador'] = request.form.get('operador')
        session['last_sos'] = request.form.get('sos')
        session['last_tipo'] = request.form.get('tipo')
        session['last_formato'] = request.form.get('formato')
        session['last_papel'] = request.form.get('papel')
        session['last_tipo_impressao'] = request.form.get('tipo_impressao')
        # Verifica se já existe um registro com este Nº OF
        num_of = safe_get_str(request.form, "num_of")
        conn = get_db_connection()
        cursor = conn.cursor()
        registro_existente = cursor.execute("SELECT id FROM producao WHERE num_of = ?", (num_of,)).fetchone()
        
        # Calcula métricas de produção
        metricas = calcular_metricas_producao(request.form)
        # Calcula o refugo total como soma das 5 colunas de refugo
        refugo_flexo = safe_get_float(request.form, "refugo_flexo", 0.0)
        refugo_pre_impresso = safe_get_float(request.form, "refugo_pre_impresso", 0.0)
        refugo_sos = safe_get_float(request.form, "refugo_sos", 0.0)
        refugo_acerto_flexo = safe_get_float(request.form, "refugo_acerto_flexo", 0.0)
        refugo_acerto_sos = safe_get_float(request.form, "refugo_acerto_sos", 0.0)
        refugo_total = refugo_flexo + refugo_pre_impresso + refugo_sos + refugo_acerto_flexo + refugo_acerto_sos
        
        # Calcula o consumo útil
        quantidade = safe_get_float(request.form, "quantidade", 0.0)
        milheiro = safe_get_float(request.form, "milheiro", 0.0)
        consumo_util = (quantidade / 1000.0) * milheiro
        
        # Calcula o consumo total
        consumo_total = consumo_util + refugo_total
        
        # Calcula tempo de acerto impressora
        tempo_acerto_impressora = 0
        if request.form.get('inicio_acerto_impressora') and request.form.get('fim_acerto_impressora'):
            inicio_s = get_seconds_from_time(request.form.get('inicio_acerto_impressora'))
            fim_s = get_seconds_from_time(request.form.get('fim_acerto_impressora'))
            tempo_acerto_impressora = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600
        
        # Calcula tempo de produção impressora
        tempo_prod_impressora = 0
        if request.form.get('inicio_prod_impressora') and request.form.get('fim_prod_impressora'):
            inicio_s = get_seconds_from_time(request.form.get('inicio_prod_impressora'))
            fim_s = get_seconds_from_time(request.form.get('fim_prod_impressora'))
            tempo_prod_impressora = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600
        
        # Insere os dados no banco - trata valores vazios
        numero_pedido = safe_get_int(request.form, "numero_pedido", None)
        refugo_robo = safe_get_float(request.form, "refugo_robo", 0.0)
        refugo_inspecao_final = safe_get_float(request.form, "refugo_inspecao_final", 0.0)
        # Calcula perdas geral (soma de perdas_un + refugo_robo + refugo_inspecao_final)
        perdas_geral = metricas["perdas_un"] + refugo_robo + refugo_inspecao_final
        perdas_geral_kg = metricas["perdas_total_kg"]
        refugo_robo_kg = metricas["refugo_robo_kg"]
        refugo_inspecao_final_kg = metricas["refugo_inspecao_final_kg"]
        # Prepara todos os valores com tratamento de valores vazios
        valores_insert = (
            safe_get_str(request.form, "num_of"),  # 1
            safe_get_str(request.form, "data"),  # 2
            safe_get_str(request.form, "data_impressora"),  # 3
            safe_get_str(request.form, "data_inspecao"),  # 4
            safe_get_str(request.form, "data_robo"),  # 5
            safe_get_str(request.form, "operador"),  # 6
            safe_get_str(request.form, "operador_impressora"),  # 7
            safe_get_str(request.form, "operador_robo"),  # 8
            safe_get_str(request.form, "impressora"),  # 9
            safe_get_str(request.form, "sos"),  # 10
            safe_get_str(request.form, "robo_alca"),  # 11
            safe_get_int(request.form, "qtd_cliches", 1),  # 11
            safe_get_str(request.form, "tipo"),  # 10
            safe_get_str(request.form, "formato"),  # 11
            safe_get_str(request.form, "papel"),  # 12
            safe_get_str(request.form, "servico"),  # 13
            milheiro,  # 14
            safe_get_str(request.form, "tipo_impressao", ""),  # 15
            refugo_flexo,  # 16
            refugo_pre_impresso,  # 17
            refugo_sos,  # 18
            refugo_robo,  # 19
            refugo_inspecao_final,  # 20
            refugo_robo_kg,  # 21
            refugo_inspecao_final_kg,  # 22
            refugo_acerto_flexo,  # 23
            refugo_acerto_sos,  # 24
            refugo_total,  # 25
            consumo_util,  # 26
            consumo_total,  # 27
            safe_get_int(request.form, "quantidade_comanda", 0),  # 28
            quantidade,  # 29
            safe_get_int(request.form, "quantidade_impressora", 0),  # 30
            safe_get_int(request.form, "quantidade_inspecao_geral", 0),  # 31
            safe_get_int(request.form, "quantidade_robo", 0),  # 32
            safe_get_str(request.form, "inicio_prod"),  # 33
            safe_get_str(request.form, "fim_prod"),  # 34
            safe_get_str(request.form, "inicio_prod_2"),  # 35
            safe_get_str(request.form, "fim_prod_2"),  # 36
            safe_get_str(request.form, "inicio_prod_impressora"),  # 37
            safe_get_str(request.form, "fim_prod_impressora"),  # 38
            safe_get_str(request.form, "inicio_acerto"),  # 39
            safe_get_str(request.form, "fim_acerto"),  # 40
            safe_get_str(request.form, "inicio_acerto_impressora"),  # 41
            safe_get_str(request.form, "fim_acerto_impressora"),  # 42
            safe_get_str(request.form, "observacoes", ""),  # 43
            metricas["refugo_pct"],  # 44
            metricas["refugo_pct_flexo"],  # 45
            metricas["eficiencia_pct"],  # 46
            metricas["velocidade_un_min"],  # 47
            metricas["velocidade_un_min_flexo"],  # 48
            metricas["perdas_un"],  # 49
            perdas_geral,  # 50
            perdas_geral_kg,  # 51
            metricas["tempo_prod_s"],  # 52
            metricas["tempo_acerto_s"],  # 53
            tempo_prod_impressora,  # 54
            tempo_acerto_impressora,  # 55
            numero_pedido  # 56
        )
        
        if registro_existente:
            # Se já existe, faz UPDATE
            registro_id = registro_existente['id']
            valores_update = valores_insert + (registro_id,)
            cursor.execute("""
                UPDATE producao SET
                    num_of=?, data=?, data_impressora=?, data_inspecao=?, data_robo=?, operador=?, operador_impressora=?, operador_robo=?, impressora=?, sos=?, robo_alca=?, qtd_cliches=?, tipo=?, formato=?, papel=?, servico=?,
                    milheiro=?, tipo_impressao=?, refugo_flexo=?, refugo_pre_impresso=?, refugo_sos=?, refugo_robo=?, refugo_inspecao_final=?, refugo_robo_kg=?, refugo_inspecao_final_kg=?, refugo_acerto_flexo=?, 
                    refugo_acerto_sos=?, refugo_producao_total=?, consumo_util=?, consumo_total=?, quantidade_comanda=?, quantidade=?, quantidade_impressora=?, quantidade_inspecao_geral=?, quantidade_robo=?, inicio_prod=?, fim_prod=?, inicio_prod_2=?, 
                    fim_prod_2=?, inicio_prod_impressora=?, fim_prod_impressora=?, inicio_acerto=?, fim_acerto=?, inicio_acerto_impressora=?, fim_acerto_impressora=?, observacoes=?, refugo_pct=?, refugo_pct_flexo=?, eficiencia_pct=?, 
                    velocidade_un_min=?, velocidade_un_min_flexo=?, perdas_un=?, perdas_geral=?, perdas_geral_kg=?, tempo_prod_s=?, tempo_acerto_s=?, tempo_prod_impressora=?, tempo_acerto_impressora=?, numero_pedido=?
                WHERE id = ?
            """, valores_update)
            flash("Dados atualizados com sucesso.", "success")
        else:
            # Se não existe, faz INSERT
            cursor.execute("""
                INSERT INTO producao (
                    num_of, data, data_impressora, data_inspecao, data_robo, operador, operador_impressora, operador_robo, impressora, sos, robo_alca, qtd_cliches, tipo, formato, papel, servico, milheiro,
                    tipo_impressao, refugo_flexo, refugo_pre_impresso, refugo_sos, refugo_robo, refugo_inspecao_final, refugo_robo_kg, refugo_inspecao_final_kg, refugo_acerto_flexo, refugo_acerto_sos, 
                    refugo_producao_total, consumo_util, consumo_total, quantidade_comanda, quantidade, quantidade_impressora, quantidade_inspecao_geral, quantidade_robo, inicio_prod, fim_prod, inicio_prod_2, fim_prod_2, inicio_prod_impressora, fim_prod_impressora, inicio_acerto, 
                    fim_acerto, inicio_acerto_impressora, fim_acerto_impressora, observacoes, refugo_pct, refugo_pct_flexo, eficiencia_pct, velocidade_un_min, velocidade_un_min_flexo, perdas_un, perdas_geral, perdas_geral_kg,
                    tempo_prod_s, tempo_acerto_s, tempo_prod_impressora, tempo_acerto_impressora, numero_pedido
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, valores_insert)
            flash("Dados lançados com sucesso.", "success")
        conn.commit()
        conn.close()
    except Exception as e:
        flash(f"Erro ao salvar no banco: {e}", "danger")
    return redirect(url_for('main.historico'))

# Rota para editar um registro existente
@main_bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = get_db_connection()
    if request.method == "POST":
        try:
            # Calcula métricas e atualiza registro
            metricas = calcular_metricas_producao(request.form)
            
            # Calcula o refugo total como soma das 5 colunas de refugo
            refugo_flexo = safe_get_float(request.form, "refugo_flexo", 0.0)
            refugo_pre_impresso = safe_get_float(request.form, "refugo_pre_impresso", 0.0)
            refugo_sos = safe_get_float(request.form, "refugo_sos", 0.0)
            refugo_acerto_flexo = safe_get_float(request.form, "refugo_acerto_flexo", 0.0)
            refugo_acerto_sos = safe_get_float(request.form, "refugo_acerto_sos", 0.0)
            refugo_total = refugo_flexo + refugo_pre_impresso + refugo_sos + refugo_acerto_flexo + refugo_acerto_sos
            
            # Calcula o consumo útil
            quantidade = safe_get_float(request.form, "quantidade", 0.0)
            milheiro = safe_get_float(request.form, "milheiro", 0.0)
            consumo_util = (quantidade / 1000.0) * milheiro
            
            # Calcula o consumo total
            consumo_total = consumo_util + refugo_total
            
            # Calcula perdas geral (soma de perdas_un + refugo_robo + refugo_inspecao_final)
            refugo_robo = safe_get_float(request.form, "refugo_robo", 0.0)
            refugo_inspecao_final = safe_get_float(request.form, "refugo_inspecao_final", 0.0)
            perdas_geral = metricas["perdas_un"] + refugo_robo + refugo_inspecao_final
            perdas_geral_kg = metricas["perdas_total_kg"]
            refugo_robo_kg = metricas["refugo_robo_kg"]
            refugo_inspecao_final_kg = metricas["refugo_inspecao_final_kg"]
            
            # Calcula tempo de acerto impressora
            tempo_acerto_impressora = 0
            if request.form.get('inicio_acerto_impressora') and request.form.get('fim_acerto_impressora'):
                inicio_s = get_seconds_from_time(request.form.get('inicio_acerto_impressora'))
                fim_s = get_seconds_from_time(request.form.get('fim_acerto_impressora'))
                tempo_acerto_impressora = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600
            
            # Calcula tempo de produção impressora
            tempo_prod_impressora = 0
            if request.form.get('inicio_prod_impressora') and request.form.get('fim_prod_impressora'):
                inicio_s = get_seconds_from_time(request.form.get('inicio_prod_impressora'))
                fim_s = get_seconds_from_time(request.form.get('fim_prod_impressora'))
                tempo_prod_impressora = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600
            
            numero_pedido = safe_get_int(request.form, "numero_pedido", None)
            conn.execute("""
                UPDATE producao SET
                    num_of=?, data=?, data_impressora=?, data_inspecao=?, data_robo=?, operador=?, operador_impressora=?, operador_robo=?, impressora=?, sos=?, robo_alca=?, qtd_cliches=?, tipo=?, formato=?, papel=?, servico=?,
                    milheiro=?, tipo_impressao=?, refugo_flexo=?, refugo_pre_impresso=?, refugo_sos=?, refugo_robo=?, refugo_inspecao_final=?, refugo_robo_kg=?, refugo_inspecao_final_kg=?, refugo_acerto_flexo=?, 
                    refugo_acerto_sos=?, refugo_producao_total=?, consumo_util=?, consumo_total=?, quantidade_comanda=?, quantidade=?, quantidade_impressora=?, quantidade_inspecao_geral=?, quantidade_robo=?, inicio_prod=?, fim_prod=?, inicio_prod_2=?, 
                    fim_prod_2=?, inicio_prod_impressora=?, fim_prod_impressora=?, inicio_acerto=?, fim_acerto=?, inicio_acerto_impressora=?, fim_acerto_impressora=?, observacoes=?, refugo_pct=?, refugo_pct_flexo=?, eficiencia_pct=?, 
                    velocidade_un_min=?, velocidade_un_min_flexo=?, perdas_un=?, perdas_geral=?, perdas_geral_kg=?, tempo_prod_s=?, tempo_acerto_s=?, tempo_prod_impressora=?, tempo_acerto_impressora=?, numero_pedido=?
                WHERE id = ?
            """, (
                safe_get_str(request.form, "num_of"), safe_get_str(request.form, "data"), safe_get_str(request.form, "data_impressora"), safe_get_str(request.form, "data_inspecao"), safe_get_str(request.form, "data_robo"),
                safe_get_str(request.form, "operador"), safe_get_str(request.form, "operador_impressora"), safe_get_str(request.form, "operador_robo"), safe_get_str(request.form, "impressora"), safe_get_str(request.form, "sos"), safe_get_str(request.form, "robo_alca"),
                safe_get_int(request.form, "qtd_cliches", 1), safe_get_str(request.form, "tipo"), safe_get_str(request.form, "formato"), safe_get_str(request.form, "papel"),
                safe_get_str(request.form, "servico"), milheiro, safe_get_str(request.form, "tipo_impressao", ""), 
                refugo_flexo, refugo_pre_impresso, refugo_sos, refugo_robo, refugo_inspecao_final, refugo_robo_kg, refugo_inspecao_final_kg, refugo_acerto_flexo, refugo_acerto_sos, refugo_total, 
                consumo_util, consumo_total, safe_get_int(request.form, "quantidade_comanda", 0), quantidade, 
                safe_get_int(request.form, "quantidade_impressora", 0), safe_get_int(request.form, "quantidade_inspecao_geral", 0), safe_get_int(request.form, "quantidade_robo", 0),
                safe_get_str(request.form, "inicio_prod"), safe_get_str(request.form, "fim_prod"), 
                safe_get_str(request.form, "inicio_prod_2"), safe_get_str(request.form, "fim_prod_2"), 
                safe_get_str(request.form, "inicio_prod_impressora"), safe_get_str(request.form, "fim_prod_impressora"), 
                safe_get_str(request.form, "inicio_acerto"), safe_get_str(request.form, "fim_acerto"), 
                safe_get_str(request.form, "inicio_acerto_impressora"), safe_get_str(request.form, "fim_acerto_impressora"), 
                safe_get_str(request.form, "observacoes", ""), metricas["refugo_pct"], metricas["refugo_pct_flexo"], 
                metricas["eficiencia_pct"], metricas["velocidade_un_min"], metricas["velocidade_un_min_flexo"], metricas["perdas_un"], perdas_geral, perdas_geral_kg,
                metricas["tempo_prod_s"], metricas["tempo_acerto_s"], tempo_prod_impressora, tempo_acerto_impressora, numero_pedido, id
            ))
            conn.commit()
            flash("Registro atualizado com sucesso.", "success")
        except Exception as e:
            flash(f"Erro ao atualizar registro: {e}", "danger")
        finally:
            conn.close()
        return redirect(url_for('main.historico'))
    # Busca o registro para edição
    lancamento = conn.execute("SELECT * FROM producao WHERE id = ?", (id,)).fetchone()
    conn.close()
    if lancamento is None:
        flash("Registro não encontrado.", "warning")
        return redirect(url_for('main.historico'))
    return render_template('index.html', page_title="Editar Lançamento", action_url=url_for('main.editar', id=id), lancamento=lancamento, operadores_sos=OPERADORES_SOS, operadores_impressora=OPERADORES_IMPRESSORA, operadores_robo=OPERADORES_ROBO)

# Rota para excluir um registro
@main_bp.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM producao WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        flash("Registro excluído com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao excluir registro: {e}", "danger")
    return redirect(url_for('main.historico'))

# Rota para exibir o histórico de lançamentos, com filtros e exportação
@main_bp.route("/historico")
def historico():
    conn = get_db_connection()
    query = "SELECT * FROM producao WHERE 1=1"
    params = []
    args = request.args.copy()
    # Filtros por operador
    selected_ops = args.getlist('operadores')
    if selected_ops:
        query += f" AND operador IN ({','.join(['?']*len(selected_ops))})"
        params.extend(selected_ops)
    # Filtros por máquina
    selected_maqs = args.getlist('maquinas')
    if selected_maqs:
        query += f" AND sos IN ({','.join(['?']*len(selected_maqs))})"
        params.extend(selected_maqs)
    # Filtros por tipo de impressão
    selected_tipos_impressao = args.getlist('tipos_impressao')
    if selected_tipos_impressao:
        query += f" AND tipo_impressao IN ({','.join(['?']*len(selected_tipos_impressao))})"
        params.extend(selected_tipos_impressao)
    # Filtro por Nº de OF
    num_of = args.get('num_of', '').strip()
    if num_of:
        query += " AND num_of LIKE ?"
        params.append(f"%{num_of}%")
    # Filtro por Serviço (busca parcial)
    servico = args.get('servico', '').strip()
    if servico:
        query += " AND servico LIKE ?"
        params.append(f"%{servico}%")
    # Filtros por data SOS
    start_date = args.get('start_date'); end_date = args.get('end_date')
    if start_date and end_date:
        query += " AND data BETWEEN ? AND ?"; params.extend([start_date, end_date])
    # Filtros por data Impressora
    start_date_impressora = args.get('start_date_impressora'); end_date_impressora = args.get('end_date_impressora')
    if start_date_impressora and end_date_impressora:
        query += " AND data_impressora BETWEEN ? AND ?"; params.extend([start_date_impressora, end_date_impressora])
    # Filtros por data Robô
    start_date_robo = args.get('start_date_robo'); end_date_robo = args.get('end_date_robo')
    if start_date_robo and end_date_robo:
        query += " AND data_robo BETWEEN ? AND ?"; params.extend([start_date_robo, end_date_robo])
    # Filtros por data Inspeção
    start_date_inspecao = args.get('start_date_inspecao'); end_date_inspecao = args.get('end_date_inspecao')
    if start_date_inspecao and end_date_inspecao:
        query += " AND data_inspecao BETWEEN ? AND ?"; params.extend([start_date_inspecao, end_date_inspecao])
    # Ordenação
    sort_by = args.get('sort_by', 'id'); sort_order = args.get('sort_order', 'desc')
    allowed_sort_columns = [
        'id', 'num_of', 'data', 'data_impressora', 'data_inspecao', 'data_robo', 'operador', 'operador_impressora', 'operador_robo', 'impressora', 'sos', 'robo_alca', 'qtd_cliches', 'tipo', 'formato', 
        'papel', 'servico', 'milheiro', 'tipo_impressao', 'quantidade_comanda', 'quantidade', 'quantidade_impressora', 'quantidade_inspecao_geral', 'quantidade_robo', 'refugo_flexo', 'refugo_pre_impresso', 'refugo_sos',
        'refugo_robo', 'refugo_inspecao_final', 'refugo_robo_kg', 'refugo_inspecao_final_kg', 'refugo_acerto_flexo', 'refugo_acerto_sos', 'refugo_pct', 'refugo_pct_flexo', 'eficiencia_pct', 'velocidade_un_min', 'velocidade_un_min_flexo', 
        'refugo_producao_total', 'consumo_util', 'consumo_total', 'perdas_un', 'perdas_geral', 'perdas_geral_kg', 'tempo_prod_s', 'tempo_acerto_s', 'tempo_prod_impressora', 'tempo_acerto_impressora', 'inicio_acerto', 'fim_acerto', 'inicio_acerto_impressora', 'fim_acerto_impressora', 'inicio_prod', 'fim_prod', 'inicio_prod_impressora', 'fim_prod_impressora', 'operador_impressora', 'numero_pedido'
    ]
    if sort_by not in allowed_sort_columns: sort_by = 'id'
    if sort_order not in ['asc', 'desc']: sort_order = 'desc'
    query += f" ORDER BY {sort_by} {sort_order}"
    # Executa consulta
    lancamentos_raw = conn.execute(query, tuple(params)).fetchall()
    lancamentos = [dict(row) for row in lancamentos_raw]
    
    # Garantir que todos os registros tenham as colunas calculadas
    for lancamento in lancamentos:
        # Calcular consumo_util se necessário
        if 'consumo_util' not in lancamento or lancamento['consumo_util'] is None or lancamento['consumo_util'] == 0:
            quantidade = lancamento.get('quantidade', 0) or 0
            milheiro = lancamento.get('milheiro', 0) or 0
            lancamento['consumo_util'] = (quantidade / 1000.0) * milheiro
        
        # Calcular consumo_total se necessário
        if 'consumo_total' not in lancamento or lancamento['consumo_total'] is None or lancamento['consumo_total'] == 0:
            consumo_util = lancamento.get('consumo_util', 0) or 0
            refugo = lancamento.get('refugo_producao_total', 0) or 0
            lancamento['consumo_total'] = consumo_util + refugo
    preserved_args = args.copy()
    preserved_args.pop('sort_by', None); preserved_args.pop('sort_order', None)
    # Exportação para Excel
    if args.get("export") == "excel":
        if lancamentos:
            # Definir a mesma ordem de colunas da tabela do histórico (conforme ordem colunas.xlsx)
            column_order = ['num_of', 'servico', 'numero_pedido', 'papel', 'formato', 'tipo', 'qtd_cliches', 'milheiro', 'quantidade_comanda', 'impressora', 'data_impressora', 'operador_impressora', 'quantidade_impressora', 'refugo_acerto_flexo', 'refugo_flexo', 'refugo_pre_impresso', 'refugo_pct_flexo', 'velocidade_un_min_flexo', 'tempo_acerto_impressora', 'tempo_prod_impressora', 'inicio_acerto_impressora', 'fim_acerto_impressora', 'inicio_prod_impressora', 'fim_prod_impressora', 'sos', 'data', 'operador', 'quantidade', 'tipo_impressao', 'refugo_acerto_sos', 'refugo_sos', 'refugo_pct', 'velocidade_un_min', 'tempo_acerto_s', 'tempo_prod_s', 'inicio_acerto', 'fim_acerto', 'inicio_prod', 'fim_prod', 'perdas_un', 'refugo_producao_total', 'consumo_util', 'consumo_total', 'robo_alca', 'data_robo', 'operador_robo', 'quantidade_robo', 'refugo_robo', 'refugo_robo_kg', 'data_inspecao', 'quantidade_inspecao_geral', 'refugo_inspecao_final', 'refugo_inspecao_final_kg', 'perdas_geral', 'perdas_geral_kg', 'observacoes', 'inicio_prod_2', 'fim_prod_2', 'eficiencia_pct']
            
            # Criar DataFrame com dados ordenados
            df_data = []
            for lancamento in lancamentos:
                row = {}
                for col in column_order:
                    if col in lancamento:
                        row[col] = lancamento[col]
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # Reordenar colunas para seguir a ordem definida
            available_columns = [col for col in column_order if col in df.columns]
            df = df[available_columns]
            
            # Renomear colunas para nomes mais amigáveis
            column_names = {
                'num_of': 'Nº OF',
                'servico': 'Serviço',
                'data': 'Data SOS',
                'data_impressora': 'Data Impressora',
                'data_inspecao': 'Data Inspeção',
                'data_robo': 'Data Robô',
                'quantidade_comanda': 'Quantidade Comanda',
                'quantidade': 'Quantidade SOS',
                'quantidade_impressora': 'Quantidade Impressora',
                'quantidade_inspecao_geral': 'Quantidade Inspeção Final',
                'quantidade_robo': 'Quantidade Robô',
                'impressora': 'Impressora',
                'sos': 'SOS',
                'robo_alca': 'Robô Alça',
                'operador': 'Operador SOS',
                'operador_impressora': 'Operador Impressora',
                'operador_robo': 'Operador Robo',
                'papel': 'Papel',
                'formato': 'Formato',
                'tipo': 'Tipo',
                'qtd_cliches': 'Qtd. Clichês',
                'milheiro': 'Peso Milheiro',
                'tipo_impressao': 'Tipo Impressão',
                'refugo_flexo': 'Refugo Flexo',
                'refugo_pre_impresso': 'Refugo Pré-Impresso',
                'refugo_sos': 'Refugo SOS',
                'refugo_robo': 'Refugo Robo (peças)',
                'refugo_inspecao_final': 'Refugo Inspeção Final (peças)',
                'refugo_robo_kg': 'Refugo Robô (kg)',
                'refugo_inspecao_final_kg': 'Refugo Inspeção Final (kg)',
                'refugo_acerto_flexo': 'Refugo Acerto Flexo',
                'refugo_acerto_sos': 'Refugo Acerto SOS',
                'refugo_producao_total': 'Refugo Produção Total (kg)',
                'consumo_util': 'Consumo Util',
                'consumo_total': 'Consumo Total',
                'inicio_acerto': 'Início Acerto SOS',
                'fim_acerto': 'Fim Acerto SOS',
                'inicio_acerto_impressora': 'Início Acerto Impressora',
                'fim_acerto_impressora': 'Fim Acerto Impressora',
                'inicio_prod': 'Início Produção SOS',
                'fim_prod': 'Fim Produção SOS',
                'inicio_prod_impressora': 'Início Produção Impressora',
                'fim_prod_impressora': 'Fim Produção Impressora',
                'tempo_acerto_s': 'Tempo Acerto SOS',
                'tempo_prod_s': 'Tempo Produção SOS',
                'tempo_acerto_impressora': 'Tempo Acerto Impressora',
                'tempo_prod_impressora': 'Tempo Produção Impressora',
                'perdas_un': 'Refugo Produção (Peças)',
                'perdas_geral': 'Refugo Geral Peças',
                'perdas_geral_kg': 'Refugo Geral (kg)',
                'inicio_prod_2': 'Início Produção 2',
                'velocidade_un_min': 'Velocidade SOS',
                'velocidade_un_min_flexo': 'Velocidade Impressora',
                'refugo_pct': 'Refugo Porcentagem SOS',
                'refugo_pct_flexo': 'Refugo Porcentagem Impressora',
                'observacoes': 'Observações'
            }
            
            df = df.rename(columns=column_names)

            # Converter Data para datetime (Excel aplicará a localidade ao exibir)
            for col in ['Data SOS', 'Data Impressora', 'Data Inspeção', 'Data Robô']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            # Manter percentuais e numéricos como valores numéricos; Excel exibirá com vírgula baseado na localidade
            numeric_cols = ['Quantidade Comanda', 'Quantidade SOS', 'Quantidade Impressora', 'Quantidade Inspeção Final', 'Quantidade Robô', 'Qtd. Clichês', 'Peso Milheiro', 'Refugo Flexo', 'Refugo Pré-Impresso', 'Refugo SOS', 'Refugo Robo (peças)', 'Refugo Inspeção Final (peças)', 'Refugo Robô (kg)', 'Refugo Inspeção Final (kg)', 'Refugo Acerto Flexo', 'Refugo Acerto SOS', 'Refugo Produção Total (kg)', 'Consumo Util', 'Consumo Total', 'Refugo Produção (Peças)', 'Refugo Geral Peças', 'Refugo Geral (kg)', 'Velocidade SOS', 'Velocidade Impressora']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            for col in ['Refugo Porcentagem SOS', 'Refugo Porcentagem Impressora', '% Eficiência']:
                if col in df.columns:
                    # Valores vêm como 1.21 para 1.21%, Excel espera 0.0121 para exibir 1.21%
                    df[col] = pd.to_numeric(df[col], errors='coerce') / 100.0

            # Converter tempo (segundos) para fração de dia (Excel) como número
            for col in ['Tempo Acerto SOS', 'Tempo Produção SOS', 'Tempo Acerto Impressora', 'Tempo Produção Impressora']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: (float(x) / 86400.0) if pd.notna(x) and x != '' and float(x) > 0 else pd.NA)
            
        else:
            df = pd.DataFrame()
        
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Historico')
                if not df.empty:
                    workbook = writer.book
                    ws = writer.sheets['Historico']
                    fmt_number = workbook.add_format({'num_format': '#,##0.00'})
                    fmt_percent = workbook.add_format({'num_format': '0.00%'})
                    fmt_time = workbook.add_format({'num_format': '[h]:mm:ss'})
                    fmt_date = workbook.add_format({'num_format': 'dd/mm/yyyy'})
                    
                    # Mapeamento de cores para cabeçalhos (cores pastel em RGB)
                    header_colors = {
                        # Verde pastel claro para datas
                        'Data Impressora': '#d4edda',
                        'Data SOS': '#d4edda',
                        'Data Robô': '#d4edda',
                        'Data Inspeção': '#d4edda',
                        # Azul pastel claro para quantidades
                        'Quantidade Comanda': '#d1ecf1',
                        'Quantidade SOS': '#d1ecf1',
                        'Quantidade Impressora': '#d1ecf1',
                        'Quantidade Inspeção Final': '#d1ecf1',
                        'Quantidade Robô': '#d1ecf1',
                        # Laranja pastel claro para impressora até tipo de impressão
                        'Impressora': '#ffeaa7',
                        'SOS': '#ffeaa7',
                        'Robô Alça': '#ffeaa7',
                        'Operador SOS': '#ffeaa7',
                        'Operador Impressora': '#ffeaa7',
                        'Operador Robo': '#ffeaa7',
                        'Papel': '#ffeaa7',
                        'Formato': '#ffeaa7',
                        'Tipo': '#ffeaa7',
                        'Qtd. Clichês': '#ffeaa7',
                        'Peso Milheiro': '#ffeaa7',
                        'Tipo Impressão': '#ffeaa7',
                        # Verde pastel claro para refugo
                        'Refugo Acerto Flexo': '#d4edda',
                        'Refugo Flexo': '#d4edda',
                        'Refugo Acerto SOS': '#d4edda',
                        'Refugo Pré-Impresso': '#d4edda',
                        'Refugo SOS': '#d4edda',
                        'Refugo Produção Total (kg)': '#d4edda',
                        # Azul pastel claro para refugo produção até consumo total
                        'Refugo Produção (Peças)': '#d1ecf1',
                        'Refugo Robo (peças)': '#d1ecf1',
                        'Refugo Inspeção Final (peças)': '#d1ecf1',
                        'Refugo Robô (kg)': '#d1ecf1',
                        'Refugo Inspeção Final (kg)': '#d1ecf1',
                        'Refugo Geral Peças': '#d1ecf1',
                        'Refugo Geral (kg)': '#d1ecf1',
                        'Consumo Util': '#d1ecf1',
                        'Consumo Total': '#d1ecf1',
                        # Amarelo pastel claro para impressora
                        'Início Acerto Impressora': '#fff9c4',
                        'Fim Acerto Impressora': '#fff9c4',
                        'Início Produção Impressora': '#fff9c4',
                        'Fim Produção Impressora': '#fff9c4',
                        'Tempo Acerto Impressora': '#fff9c4',
                        'Tempo Produção Impressora': '#fff9c4',
                        # Verde pastel claro para SOS
                        'Início Acerto SOS': '#d4edda',
                        'Fim Acerto SOS': '#d4edda',
                        'Início Produção SOS': '#d4edda',
                        'Fim Produção SOS': '#d4edda',
                        'Tempo Acerto SOS': '#d4edda',
                        'Tempo Produção SOS': '#d4edda',
                    }
                    
                    # Formatar cabeçalho com cores
                    for i, col in enumerate(df.columns):
                        bg_color = header_colors.get(col, '#f8f9fa')  # Cor padrão se não encontrada
                        header_format = workbook.add_format({
                            'bold': True,
                            'bg_color': bg_color,
                            'border': 1,
                            'align': 'center',
                            'valign': 'vcenter'
                        })
                        ws.write(0, i, col, header_format)
                    
                    # Aplicar formatos por coluna e ajustar largura (evitar len() em float)
                    for i, col in enumerate(df.columns):
                        s = df[col].apply(lambda x: str(x) if pd.notna(x) else '')
                        width = max(int(s.str.len().max()) if len(s) > 0 else 0, len(col)) + 2
                        if col in ['Refugo Porcentagem SOS', 'Refugo Porcentagem Impressora', '% Eficiência']:
                            ws.set_column(i, i, width, fmt_percent)
                        elif col in numeric_cols:
                            ws.set_column(i, i, width, fmt_number)
                        elif col in ['Tempo Acerto SOS', 'Tempo Produção SOS', 'Tempo Acerto Impressora', 'Tempo Produção Impressora']:
                            ws.set_column(i, i, width, fmt_time)
                        elif col in ['Data SOS', 'Data Impressora', 'Data Inspeção', 'Data Robô']:
                            ws.set_column(i, i, width, fmt_date)
                        else:
                            ws.set_column(i, i, width)
            output.seek(0); conn.close()
            return send_file(output, download_name="historico_producao.xlsx", as_attachment=True)
        except Exception as e:
            flash(f"Erro ao exportar: {e}", "danger"); return redirect(url_for('main.historico'))
    conn.close()
    return render_template('historico.html', lancamentos=lancamentos, all_operadores=ALL_OPERADORES, preserved_args=preserved_args, action_url=url_for('main.historico'))

# Rota OF-Refugo (histórico simplificado)
@main_bp.route("/of-refugo")
def of_refugo():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM producao", conn)
    conn.close()
    
    lancamentos = []
    
    if not df.empty:
        # Aplicar filtros
        servico = request.args.get('servico', '').strip()
        if servico:
            df = df[df['servico'].str.contains(servico, case=False, na=False)]
        num_of = request.args.get('num_of', '').strip()
        if num_of:
            df = df[df['num_of'].str.contains(num_of, case=False, na=False)]
        numero_pedido = request.args.get('numero_pedido', '').strip()
        if numero_pedido and 'numero_pedido' in df.columns:
            df = df[df['numero_pedido'].astype(str).str.contains(numero_pedido, case=False, na=False)]
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            df = df[(df['data'] >= start_date) & (df['data'] <= end_date)]
        start_date_impressora = request.args.get('start_date_impressora')
        end_date_impressora = request.args.get('end_date_impressora')
        if start_date_impressora and end_date_impressora:
            df = df[(df['data_impressora'] >= start_date_impressora) & (df['data_impressora'] <= end_date_impressora)]
        start_date_robo = request.args.get('start_date_robo')
        end_date_robo = request.args.get('end_date_robo')
        if start_date_robo and end_date_robo:
            df = df[(df['data_robo'] >= start_date_robo) & (df['data_robo'] <= end_date_robo)]
        start_date_inspecao = request.args.get('start_date_inspecao')
        end_date_inspecao = request.args.get('end_date_inspecao')
        if start_date_inspecao and end_date_inspecao:
            df = df[(df['data_inspecao'] >= start_date_inspecao) & (df['data_inspecao'] <= end_date_inspecao)]
        selected_operadores = request.args.getlist('operadores')
        if selected_operadores:
            df = df[df['operador'].isin(selected_operadores)]
        selected_maquinas = request.args.getlist('maquinas')
        if selected_maquinas:
            df = df[df['sos'].isin(selected_maquinas)]
        selected_tipos_impressao = request.args.getlist('tipos_impressao')
        if selected_tipos_impressao:
            df = df[df['tipo_impressao'].isin(selected_tipos_impressao)]
        
        # Ordenação: por padrão Data Inspeção Final (mais recente primeiro)
        sort_by = request.args.get('sort_by', 'data_inspecao')
        sort_order = request.args.get('sort_order', 'desc')
        allowed_sort_columns = [
            'id', 'num_of', 'data_inspecao', 'quantidade_comanda', 'quantidade_inspecao_geral', 
            'perdas_un', 'refugo_robo', 'refugo_inspecao_final', 'perdas_geral', 'pct_refugo_pedido', 'refugo_flexo_kg', 'refugo_sos_kg', 'consumo_total',
            'servico', 'numero_pedido'
        ]
        if sort_by not in allowed_sort_columns:
            sort_by = 'data_inspecao'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        if sort_by in df.columns:
            if sort_by == 'data_inspecao':
                df[sort_by] = pd.to_datetime(df[sort_by], errors='coerce')
            df = df.sort_values(by=sort_by, ascending=(sort_order == 'asc'), na_position='last')
            # Reverter data_inspecao para string YYYY-MM-DD para o template exibir DD/MM/YYYY sem horário
            if sort_by == 'data_inspecao' and 'data_inspecao' in df.columns:
                df['data_inspecao'] = df['data_inspecao'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        
        # Converter para lista de dicionários
        lancamentos = df.to_dict('records')
        
        # Importar math para arredondar para cima
        import math
        
        # Calcular consumo_total e arredondar quantidades e refugos para cima
        campos_arredondar = ['quantidade_comanda', 'quantidade_inspecao_geral', 'perdas_un', 'refugo_robo', 'refugo_inspecao_final', 'perdas_geral']
        for lancamento in lancamentos:
            # Arredondar quantidades e refugos para cima
            for campo in campos_arredondar:
                if campo in lancamento and lancamento[campo] is not None:
                    try:
                        valor = float(lancamento[campo])
                        lancamento[campo] = math.ceil(valor)
                    except (ValueError, TypeError):
                        pass
            
            # Refugo Flexo (kg) = refugo_acerto_flexo + refugo_flexo + refugo_pre_impresso
            refugo_acerto_flexo = float(lancamento.get('refugo_acerto_flexo', 0) or 0)
            refugo_flexo = float(lancamento.get('refugo_flexo', 0) or 0)
            refugo_pre_impresso = float(lancamento.get('refugo_pre_impresso', 0) or 0)
            lancamento['refugo_flexo_kg'] = refugo_acerto_flexo + refugo_flexo + refugo_pre_impresso
            
            # Refugo SOS (kg) = refugo_acerto_sos + refugo_sos (sem refugo_pre_impresso na tela OF-Refugo)
            refugo_acerto_sos = float(lancamento.get('refugo_acerto_sos', 0) or 0)
            refugo_sos = float(lancamento.get('refugo_sos', 0) or 0)
            lancamento['refugo_sos_kg'] = refugo_acerto_sos + refugo_sos
            
            # Calcular consumo_total se necessário
            if 'consumo_total' not in lancamento or lancamento['consumo_total'] is None or lancamento['consumo_total'] == 0:
                consumo_util = lancamento.get('consumo_util', 0) or 0
                refugo = lancamento.get('refugo_producao_total', 0) or 0
                lancamento['consumo_total'] = consumo_util + refugo
            
            # Porcentagem de Refugo Pedido = (Refugo Geral Peças / Qtde Inspeção Final) × 100
            qtd_inspecao = float(lancamento.get('quantidade_inspecao_geral', 0) or 0)
            perdas_geral_val = float(lancamento.get('perdas_geral', 0) or 0)
            lancamento['pct_refugo_pedido'] = (perdas_geral_val / qtd_inspecao * 100) if qtd_inspecao > 0 else None
    
    preserved_args = request.args.to_dict()
    preserved_args.pop('sort_by', None)
    preserved_args.pop('sort_order', None)
    
    # Exportação para Excel
    if request.args.get("export") == "excel":
        if lancamentos:
            # Campos simplificados para exibir
            column_order = ['num_of', 'servico', 'numero_pedido', 'data_inspecao', 'quantidade_comanda', 'quantidade_inspecao_geral', 'perdas_geral', 'pct_refugo_pedido', 'perdas_un', 'refugo_robo', 'refugo_inspecao_final', 'refugo_flexo_kg', 'refugo_sos_kg', 'consumo_total']
            
            df_data = []
            for lancamento in lancamentos:
                row = {}
                for col in column_order:
                    if col in lancamento:
                        row[col] = lancamento[col]
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            available_columns = [col for col in column_order if col in df.columns]
            df = df[available_columns]
            
            column_names = {
                'num_of': 'Nº OF',
                'servico': 'Serviço',
                'numero_pedido': 'Número do Pedido',
                'data_inspecao': 'Data Inspeção Final',
                'quantidade_comanda': 'Qtde Comanda',
                'quantidade_inspecao_geral': 'Qtde Inspeção Final',
                'perdas_un': 'Refugo Produção (peças)',
                'refugo_robo': 'Refugo Robo (peças)',
                'refugo_inspecao_final': 'Refugo Inspeção Final (peças)',
                'perdas_geral': 'Refugo Geral Peças',
                'pct_refugo_pedido': 'Porcentagem de Refugo Pedido',
                'refugo_flexo_kg': 'Refugo Flexo (kg)',
                'refugo_sos_kg': 'Refugo SOS (kg)',
                'consumo_total': 'Consumo Total (kg)'
            }
            df = df.rename(columns=column_names)
            
            for col in ['Data Inspeção Final']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            import math
            # Campos numéricos inteiros (arredondados para cima)
            int_cols = ['Número do Pedido', 'Qtde Comanda', 'Qtde Inspeção Final', 'Refugo Produção (peças)', 'Refugo Robo (peças)', 'Refugo Inspeção Final (peças)', 'Refugo Geral Peças']
            for col in int_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').apply(lambda x: math.ceil(x) if pd.notna(x) else x).astype('Int64')
            
            # Campos numéricos decimais
            numeric_cols = ['Refugo Flexo (kg)', 'Refugo SOS (kg)', 'Consumo Total (kg)']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            # Porcentagem de Refugo Pedido: converter de 5.5 para 0.055 para formato % no Excel
            if 'Porcentagem de Refugo Pedido' in df.columns:
                df['Porcentagem de Refugo Pedido'] = pd.to_numeric(df['Porcentagem de Refugo Pedido'], errors='coerce') / 100.0
            
            output = BytesIO()
            try:
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='OF-Refugo')
                    if not df.empty:
                        workbook = writer.book
                        ws = writer.sheets['OF-Refugo']
                        fmt_number = workbook.add_format({'num_format': '#,##0.00'})
                        fmt_int = workbook.add_format({'num_format': '#,##0'})
                        fmt_date = workbook.add_format({'num_format': 'dd/mm/yyyy'})
                        fmt_percent = workbook.add_format({'num_format': '0.00%'})
                        
                        # Cores para cabeçalhos específicos
                        header_colors = {
                            'Refugo Flexo (kg)': '#ffeaa7',  # Laranja pastel clarinho
                            'Refugo SOS (kg)': '#ffeaa7',     # Laranja pastel clarinho
                            'Consumo Total (kg)': '#ffeaa7',  # Laranja pastel clarinho
                            'Porcentagem de Refugo Pedido': '#d4edda'  # Verde pastel (igual Refugo Geral)
                        }
                        
                        for i, col in enumerate(df.columns):
                            bg_color = header_colors.get(col, '#f8f9fa')  # Cor padrão se não encontrada
                            header_format = workbook.add_format({
                                'bold': True,
                                'bg_color': bg_color,
                                'border': 1,
                                'align': 'center',
                                'valign': 'vcenter'
                            })
                            ws.write(0, i, col, header_format)
                            s = df[col].apply(lambda x: str(x) if pd.notna(x) else '')
                            width = max(int(s.str.len().max()) if len(s) > 0 else 0, len(col)) + 2
                            if col in int_cols:
                                ws.set_column(i, i, width, fmt_int)
                            elif col in numeric_cols:
                                ws.set_column(i, i, width, fmt_number)
                            elif col == 'Porcentagem de Refugo Pedido':
                                ws.set_column(i, i, width, fmt_percent)
                            elif col == 'Data Inspeção Final':
                                ws.set_column(i, i, width, fmt_date)
                            else:
                                ws.set_column(i, i, width)
                output.seek(0)
                return send_file(output, download_name="of_refugo.xlsx", as_attachment=True)
            except Exception as e:
                flash(f"Erro ao exportar: {e}", "danger")
                return redirect(url_for('main.of_refugo'))
    
    return render_template('historico_simplificado.html', lancamentos=lancamentos, all_operadores=ALL_OPERADORES, preserved_args=preserved_args, action_url=url_for('main.of_refugo'))

@main_bp.route("/historico_simplificado")
def historico_simplificado_redirect():
    """Redirect da URL antiga para /of-refugo (preserva filtros e parâmetros)."""
    return redirect(url_for('main.of_refugo', **request.args))

# Comparação Quantidade (duplicata OF-Refugo com colunas específicas + Refugo SOS Peças e Diferença)
@main_bp.route("/comparacao-quantidade")
def comparacao_quantidade():
    import math
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM producao", conn)
    conn.close()

    lancamentos = []

    if not df.empty:
        servico = request.args.get('servico', '').strip()
        if servico:
            df = df[df['servico'].str.contains(servico, case=False, na=False)]
        num_of = request.args.get('num_of', '').strip()
        if num_of:
            df = df[df['num_of'].str.contains(num_of, case=False, na=False)]
        numero_pedido = request.args.get('numero_pedido', '').strip()
        if numero_pedido and 'numero_pedido' in df.columns:
            df = df[df['numero_pedido'].astype(str).str.contains(numero_pedido, case=False, na=False)]
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            df = df[(df['data'] >= start_date) & (df['data'] <= end_date)]
        start_date_impressora = request.args.get('start_date_impressora')
        end_date_impressora = request.args.get('end_date_impressora')
        if start_date_impressora and end_date_impressora:
            df = df[(df['data_impressora'] >= start_date_impressora) & (df['data_impressora'] <= end_date_impressora)]
        start_date_robo = request.args.get('start_date_robo')
        end_date_robo = request.args.get('end_date_robo')
        if start_date_robo and end_date_robo:
            df = df[(df['data_robo'] >= start_date_robo) & (df['data_robo'] <= end_date_robo)]
        start_date_inspecao = request.args.get('start_date_inspecao')
        end_date_inspecao = request.args.get('end_date_inspecao')
        if start_date_inspecao and end_date_inspecao:
            df = df[(df['data_inspecao'] >= start_date_inspecao) & (df['data_inspecao'] <= end_date_inspecao)]
        selected_operadores = request.args.getlist('operadores')
        if selected_operadores:
            df = df[df['operador'].isin(selected_operadores)]
        selected_maquinas = request.args.getlist('maquinas')
        if selected_maquinas:
            df = df[df['sos'].isin(selected_maquinas)]
        selected_tipos_impressao = request.args.getlist('tipos_impressao')
        if selected_tipos_impressao:
            df = df[df['tipo_impressao'].isin(selected_tipos_impressao)]

        # Comparação Quantidade: excluir linhas com quantidade_impressora 0 ou null
        if 'quantidade_impressora' in df.columns:
            df = df[(df['quantidade_impressora'].notna()) & (df['quantidade_impressora'] != 0)]
        # Excluir linhas com Quantidade SOS igual a 0
        if 'quantidade' in df.columns:
            df = df[(df['quantidade'].notna()) & (df['quantidade'] != 0)]

        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')
        allowed_sort = [
            'id', 'num_of', 'servico', 'numero_pedido', 'quantidade_comanda', 'quantidade_impressora', 'quantidade',
            'refugo_sos_pecas', 'diferenca', 'observacoes'
        ]
        if sort_by not in allowed_sort:
            sort_by = 'id'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'

        rows = df.to_dict('records')
        for r in rows:
            ras = float(r.get('refugo_acerto_sos', 0) or 0)
            rpi = float(r.get('refugo_pre_impresso', 0) or 0)
            rs = float(r.get('refugo_sos', 0) or 0)
            refugo_sos_kg = ras + rpi + rs
            m = float(r.get('milheiro', 0) or 0)
            refugo_sos_pecas = math.ceil((refugo_sos_kg * 1000) / m) if m > 0 else 0
            qsos = int(r.get('quantidade', 0) or 0)
            qimp = int(r.get('quantidade_impressora', 0) or 0)
            diferenca = (qsos + refugo_sos_pecas) - qimp

            rec = {
                'id': r.get('id'),
                'num_of': r.get('num_of'),
                'servico': r.get('servico'),
                'numero_pedido': r.get('numero_pedido'),
                'quantidade_comanda': r.get('quantidade_comanda'),
                'quantidade': r.get('quantidade'),
                'quantidade_impressora': r.get('quantidade_impressora'),
                'refugo_sos_pecas': refugo_sos_pecas,
                'diferenca': diferenca,
                'observacoes': r.get('observacoes'),
            }
            if rec['quantidade_comanda'] is not None:
                try:
                    rec['quantidade_comanda'] = math.ceil(float(rec['quantidade_comanda']))
                except (ValueError, TypeError):
                    pass
            lancamentos.append(rec)

        if lancamentos and sort_by in allowed_sort:
            d = pd.DataFrame(lancamentos)
            if sort_by in d.columns:
                d = d.sort_values(by=sort_by, ascending=(sort_order == 'asc'), na_position='last')
            lancamentos = d.to_dict('records')

    preserved_args = request.args.to_dict()
    preserved_args.pop('sort_by', None)
    preserved_args.pop('sort_order', None)

    if request.args.get("export") == "excel" and lancamentos:
        column_order = ['num_of', 'servico', 'numero_pedido', 'quantidade_comanda', 'quantidade_impressora', 'quantidade', 'refugo_sos_pecas', 'diferenca', 'observacoes']
        column_names = {
            'num_of': 'Nº OF', 'servico': 'Serviço', 'numero_pedido': 'Número do Pedido',
            'quantidade_comanda': 'Quantidade Comanda', 'quantidade': 'Quantidade SOS', 'quantidade_impressora': 'Quantidade Impressora',
            'refugo_sos_pecas': 'Refugo SOS Peças', 'diferenca': 'Diferença', 'observacoes': 'Observações'
        }
        df_out = pd.DataFrame(lancamentos)
        df_out = df_out[[c for c in column_order if c in df_out.columns]]
        df_out = df_out.rename(columns=column_names)
        int_cols = ['Número do Pedido', 'Quantidade Comanda', 'Quantidade SOS', 'Quantidade Impressora', 'Refugo SOS Peças', 'Diferença']
        for col in int_cols:
            if col in df_out.columns:
                df_out[col] = pd.to_numeric(df_out[col], errors='coerce').apply(lambda x: math.ceil(x) if pd.notna(x) else x).astype('Int64')
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_out.to_excel(writer, index=False, sheet_name='Comparacao Quantidade')
                if not df_out.empty:
                    wb = writer.book
                    ws = writer.sheets['Comparacao Quantidade']
                    fmt = wb.add_format({'bold': True, 'bg_color': '#f8f9fa', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                    fmt_int = wb.add_format({'num_format': '#,##0'})
                    int_cols = ['Número do Pedido', 'Quantidade Comanda', 'Quantidade SOS', 'Quantidade Impressora', 'Refugo SOS Peças', 'Diferença']
                    for i, col in enumerate(df_out.columns):
                        ws.write(0, i, col, fmt)
                        mx = df_out.iloc[:, i].astype(str).str.len().max()
                        w = max(int(mx) if pd.notna(mx) else 0, len(str(col))) + 2
                        ws.set_column(i, i, w, fmt_int if col in int_cols else None)
            output.seek(0)
            return send_file(output, download_name="comparacao_quantidade.xlsx", as_attachment=True)
        except Exception as e:
            flash(f"Erro ao exportar: {e}", "danger")
            return redirect(url_for('main.comparacao_quantidade'))

    return render_template('comparacao_quantidade.html', lancamentos=lancamentos, all_operadores=ALL_OPERADORES, preserved_args=preserved_args, action_url=url_for('main.comparacao_quantidade'))

# Comparativo Mensal: métricas mês a mês (Quantidade SOS, Meta Alcançada, % Refugo SOS, % Refugo SOS+Flexo)
@main_bp.route("/comparativo-mensal", methods=["GET", "POST"])
def comparativo_mensal():
    from datetime import datetime
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, data, quantidade, quantidade_impressora, milheiro, refugo_acerto_sos, refugo_pre_impresso, refugo_sos, refugo_producao_total, refugo_pct, tipo_impressao, consumo_total FROM producao", conn)
    
    # Processar salvamento de metas mensais (POST)
    if request.method == "POST":
        ano_meta = request.form.get("ano_meta")
        if ano_meta:
            try:
                ano_meta = int(ano_meta)
                cursor = conn.cursor()
                for mes in range(1, 13):
                    meta_key = f"meta_mes_{mes}"
                    meta_val = request.form.get(meta_key, "").strip().replace(".", "").replace(",", ".")
                    if meta_val:
                        try:
                            meta_quantidade = float(meta_val)
                            if meta_quantidade > 0:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO metas_mensais (ano, mes, meta_quantidade)
                                    VALUES (?, ?, ?)
                                """, (ano_meta, mes, meta_quantidade))
                        except (ValueError, TypeError):
                            pass
                conn.commit()
                conn.close()
                # Redirecionar após salvar para mostrar dados atualizados
                return redirect(url_for("main.comparativo_mensal", ano=ano_meta))
            except (ValueError, TypeError):
                pass
    
    conn.close()

    # Meta padrão (para compatibilidade com código antigo)
    meta_quantidade_padrao = 1000000.0
    try:
        m = request.args.get("meta_quantidade", "1000000").strip().replace(".", "").replace(",", ".")
        if m:
            meta_quantidade_padrao = float(m)
    except (ValueError, TypeError):
        pass
    if meta_quantidade_padrao <= 0:
        meta_quantidade_padrao = 1000000.0

    MESES_NOME = (
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    )

    rows_mensal = []
    ano_used = None
    df_ano = None
    metas_dict = {}  # Inicializar metas_dict antes do bloco
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df = df[df["data"].notna()]
        if not df.empty:
            df["mes"] = df["data"].dt.month
            df["ano"] = df["data"].dt.year.astype(int)
            df_ano = df.copy()
            # Definir ano: da URL ou o maior ano presente nos dados (evita misturar anos)
            ano_filtro = (request.args.get("ano") or "").strip()
            if ano_filtro:
                try:
                    ano_used = int(ano_filtro)
                except ValueError:
                    ano_used = None
            if ano_used is None and not df["ano"].empty:
                ano_used = int(df["ano"].max())
            # Sempre filtrar por ano antes de agregar (só conta data SOS no ano escolhido)
            if ano_used is not None:
                df = df.loc[df["ano"] == ano_used].copy()

            # Carregar metas mensais do banco de dados
            if ano_used is not None:
                conn_meta = get_db_connection()
                cursor_meta = conn_meta.cursor()
                cursor_meta.execute("SELECT mes, meta_quantidade FROM metas_mensais WHERE ano = ?", (ano_used,))
                for row in cursor_meta.fetchall():
                    metas_dict[row["mes"]] = row["meta_quantidade"]
                conn_meta.close()
            df["rsos_kg"] = (df["refugo_acerto_sos"].fillna(0) + df["refugo_pre_impresso"].fillna(0) + df["refugo_sos"].fillna(0))
            df["peso_boas_sos"] = df["quantidade"].fillna(0) * (df["milheiro"].fillna(0) / 1000)
            df["refugo_total_kg"] = df["refugo_producao_total"].fillna(0)
            df["peso_boas_total"] = (df["quantidade"].fillna(0) + df["quantidade_impressora"].fillna(0)) * (df["milheiro"].fillna(0) / 1000)

            for mes in range(1, 13):
                # Considerar só registros do ano selecionado E do mês (evita “vazar” outros anos)
                dm = df[(df["ano"] == ano_used) & (df["mes"] == mes)] if ano_used is not None else df[df["mes"] == mes]
                meta_mes = metas_dict.get(mes, meta_quantidade_padrao)
                if dm.empty:
                    rows_mensal.append({
                        "mes_num": mes,
                        "mes_nome": MESES_NOME[mes - 1],
                        "quantidade_mes": 0,
                        "meta_alcancada": 0.0,
                        "meta_quantidade": meta_mes,
                        "pct_refugo_sos": None,
                        "pct_refugo_sos_flexo": None,
                    })
                    continue
                quant_mes = int(dm["quantidade"].sum())
                soma_rsos = dm["rsos_kg"].sum()
                soma_peso_sos = dm["peso_boas_sos"].sum()
                den_sos = soma_peso_sos + soma_rsos
                pct_sos = (soma_rsos / den_sos * 100) if den_sos > 0 else None
                soma_refugo_total = dm["refugo_total_kg"].sum()
                den_sos_flexo = soma_peso_sos + soma_refugo_total
                pct_sos_flexo = (soma_refugo_total / den_sos_flexo * 100) if den_sos_flexo > 0 else None

                meta_pct = (quant_mes / meta_mes * 100) if meta_mes > 0 else 0.0

                rows_mensal.append({
                    "mes_num": mes,
                    "mes_nome": MESES_NOME[mes - 1],
                    "quantidade_mes": quant_mes,
                    "meta_alcancada": meta_pct,
                    "meta_quantidade": meta_mes,
                    "pct_refugo_sos": pct_sos,
                    "pct_refugo_sos_flexo": pct_sos_flexo,
                })

    if len(rows_mensal) < 12:
        existentes = {r["mes_num"] for r in rows_mensal}
        for mes in range(1, 13):
            if mes not in existentes:
                meta_mes = metas_dict.get(mes, meta_quantidade_padrao)
                rows_mensal.append({
                    "mes_num": mes,
                    "mes_nome": MESES_NOME[mes - 1],
                    "quantidade_mes": 0,
                    "meta_alcancada": 0.0,
                    "meta_quantidade": meta_mes,
                    "pct_refugo_sos": None,
                    "pct_refugo_sos_flexo": None,
                })
        rows_mensal.sort(key=lambda x: x["mes_num"])

    # Total geral
    total_quant = sum(r["quantidade_mes"] for r in rows_mensal)
    # Meta Alcançada: média das metas alcançadas (não soma das porcentagens)
    meta_alcancadas = [r["meta_alcancada"] for r in rows_mensal if r.get("meta_alcancada") is not None]
    total_meta_pct = sum(meta_alcancadas) / len(meta_alcancadas) if meta_alcancadas else None
    # Refugo SOS: percentual consolidado do período (refugo_sos / (peso_boas_sos + refugo_sos) × 100)
    total_pct_sos = None
    total_pct_sos_flexo = None
    if not df.empty and "rsos_kg" in df.columns:
        soma_rsos_g = df["rsos_kg"].sum()
        soma_peso_sos_g = df["peso_boas_sos"].sum()
        den_g = soma_peso_sos_g + soma_rsos_g
        total_pct_sos = (soma_rsos_g / den_g * 100) if den_g > 0 else None
        soma_rt_g = df["refugo_total_kg"].sum()
        den_tg_sos = soma_peso_sos_g + soma_rt_g
        total_pct_sos_flexo = (soma_rt_g / den_tg_sos * 100) if den_tg_sos > 0 else None

    anos_disponiveis = [datetime.now().year]
    if df_ano is not None and not df_ano.empty and "ano" in df_ano.columns:
        anos_disponiveis = sorted(df_ano["ano"].dropna().unique().astype(int).tolist(), reverse=True)
    ano_selecionado = request.args.get("ano")
    if not ano_selecionado:
        ano_selecionado = str(ano_used) if ano_used is not None else str(anos_disponiveis[0])
    
    # Garantir que ano_used esteja definido mesmo sem dados
    if ano_used is None:
        try:
            ano_used = int(ano_selecionado)
        except (ValueError, TypeError):
            ano_used = datetime.now().year
    
    # Carregar metas mensais se ainda não carregadas (quando não há dados no df)
    if ano_used is not None and not metas_dict:
        conn_meta = get_db_connection()
        cursor_meta = conn_meta.cursor()
        cursor_meta.execute("SELECT mes, meta_quantidade FROM metas_mensais WHERE ano = ?", (ano_used,))
        for row in cursor_meta.fetchall():
            metas_dict[row["mes"]] = row["meta_quantidade"]
        conn_meta.close()

    for r in rows_mensal:
        r["quantidade_mes_fmt"] = f"{r['quantidade_mes']:,}".replace(",", ".")
        r["meta_alcancada_fmt"] = f"{r['meta_alcancada']:.2f}".replace(".", ",") + "%" if r["meta_alcancada"] is not None else "—"
        r["pct_refugo_sos_fmt"] = f"{r['pct_refugo_sos']:.2f}".replace(".", ",") + "%" if r.get("pct_refugo_sos") is not None else "—"
        r["pct_refugo_sos_flexo_fmt"] = f"{r['pct_refugo_sos_flexo']:.2f}".replace(".", ",") + "%" if r.get("pct_refugo_sos_flexo") is not None else "—"
    total_quantidade_fmt = f"{total_quant:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    total_meta_fmt = f"{total_meta_pct:.2f}".replace(".", ",") + "%" if total_meta_pct is not None else "—"
    total_pct_sos_fmt = f"{total_pct_sos:.2f}".replace(".", ",") + "%" if total_pct_sos is not None else "—"
    total_pct_sos_flexo_fmt = f"{total_pct_sos_flexo:.2f}".replace(".", ",") + "%" if total_pct_sos_flexo is not None else "—"

    # Preparar dados para a segunda tabela (Consumo e Produção por Tipo)
    rows_producao_tipo = []
    
    # Processar dados mensais para a segunda tabela
    for mes in range(1, 13):
        if not df.empty and ano_used is not None:
            dm = df[(df["ano"] == ano_used) & (df["mes"] == mes)]
        else:
            dm = pd.DataFrame()
        
        if dm.empty:
            rows_producao_tipo.append({
                "mes_num": mes,
                "mes_nome": MESES_NOME[mes - 1],
                "consumo_total": 0,
                "refugo_producao_total_kg": 0,
                "pct_producao_sos": None,
                "pct_producao_pre_impresso": None,
            })
            continue
        
        # Consumo Total
        consumo_total = dm["consumo_total"].fillna(0).sum() if "consumo_total" in dm.columns else 0
        
        # Refugo Produção Total (kg)
        refugo_producao_total_kg = dm["refugo_producao_total"].fillna(0).sum() if "refugo_producao_total" in dm.columns else 0
        
        # Quantidade total produzida do mês (apenas SOS, campo "quantidade")
        # O tipo_impressao se refere apenas à produção SOS, então usamos apenas "quantidade" como base
        quantidade_total = 0
        if "quantidade" in dm.columns:
            quantidade_total = dm["quantidade"].fillna(0).sum()
        
        # Quantidade por tipo de impressão (baseado na produção SOS, campo "quantidade")
        quantidade_sos = 0
        quantidade_pre_impresso = 0
        
        if "tipo_impressao" in dm.columns and "quantidade" in dm.columns:
            dm_tipo = dm.copy()
            dm_tipo["tipo_impressao"] = dm_tipo["tipo_impressao"].fillna("").str.strip()
            # Quantidade produzida como SOS (tipo_impressao = "SOS")
            quantidade_sos = dm_tipo[dm_tipo["tipo_impressao"].str.upper() == "SOS"]["quantidade"].fillna(0).sum()
            # Quantidade produzida como Pré-Impresso (tipo_impressao = "Pré-Impresso")
            mask_pre_impresso = dm_tipo["tipo_impressao"].str.upper().isin(["PRÉ-IMPRESSO", "PRE-IMPRESSO", "PRÉ IMPRESSO", "PRE IMPRESSO"])
            quantidade_pre_impresso = dm_tipo[mask_pre_impresso]["quantidade"].fillna(0).sum()
        
        # Percentuais em relação à quantidade total do mês (quantidade SOS)
        # A soma dos dois percentuais deve dar 100% (ou próximo, se houver valores sem tipo definido)
        pct_producao_sos = (quantidade_sos / quantidade_total * 100) if quantidade_total > 0 else None
        pct_producao_pre_impresso = (quantidade_pre_impresso / quantidade_total * 100) if quantidade_total > 0 else None
        
        rows_producao_tipo.append({
            "mes_num": mes,
            "mes_nome": MESES_NOME[mes - 1],
            "consumo_total": consumo_total,
            "refugo_producao_total_kg": refugo_producao_total_kg,
            "pct_producao_sos": pct_producao_sos,
            "pct_producao_pre_impresso": pct_producao_pre_impresso,
        })
    
    # Formatar valores da segunda tabela
    for r in rows_producao_tipo:
        r["consumo_total_fmt"] = f"{r['consumo_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if r["consumo_total"] > 0 else "—"
        r["refugo_producao_total_kg_fmt"] = f"{r['refugo_producao_total_kg']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if r["refugo_producao_total_kg"] > 0 else "—"
        r["pct_producao_sos_fmt"] = f"{r['pct_producao_sos']:.2f}".replace(".", ",") + "%" if r.get("pct_producao_sos") is not None else "—"
        r["pct_producao_pre_impresso_fmt"] = f"{r['pct_producao_pre_impresso']:.2f}".replace(".", ",") + "%" if r.get("pct_producao_pre_impresso") is not None else "—"
    
    # Totais da segunda tabela
    total_consumo_total = sum(r["consumo_total"] for r in rows_producao_tipo)
    total_refugo_producao_total_kg = sum(r["refugo_producao_total_kg"] for r in rows_producao_tipo)
    
    # Calcular percentuais totais (consolidado do ano)
    if not df.empty and ano_used is not None and "tipo_impressao" in df.columns:
        df_ano_filtrado = df[df["ano"] == ano_used] if ano_used is not None else df
        df_ano_filtrado_tipo = df_ano_filtrado.copy()
        df_ano_filtrado_tipo["tipo_impressao"] = df_ano_filtrado_tipo["tipo_impressao"].fillna("").str.strip()
        
        if "quantidade" in df_ano_filtrado.columns:
            # Quantidade total do ano (apenas SOS, campo "quantidade")
            quantidade_total_geral = df_ano_filtrado["quantidade"].fillna(0).sum()
            # Quantidade produzida como SOS no ano
            quantidade_sos_geral = df_ano_filtrado_tipo[df_ano_filtrado_tipo["tipo_impressao"].str.upper() == "SOS"]["quantidade"].fillna(0).sum()
            # Quantidade produzida como Pré-Impresso no ano
            mask_pre_impresso_geral = df_ano_filtrado_tipo["tipo_impressao"].str.upper().isin(["PRÉ-IMPRESSO", "PRE-IMPRESSO", "PRÉ IMPRESSO", "PRE IMPRESSO"])
            quantidade_pre_impresso_geral = df_ano_filtrado_tipo[mask_pre_impresso_geral]["quantidade"].fillna(0).sum()
            
            # Percentuais em relação à quantidade total do ano (quantidade SOS)
            # A soma dos dois percentuais deve dar 100% (ou próximo, se houver valores sem tipo definido)
            total_pct_producao_sos = (quantidade_sos_geral / quantidade_total_geral * 100) if quantidade_total_geral > 0 else None
            total_pct_producao_pre_impresso = (quantidade_pre_impresso_geral / quantidade_total_geral * 100) if quantidade_total_geral > 0 else None
        else:
            total_pct_producao_sos = None
            total_pct_producao_pre_impresso = None
    else:
        total_pct_producao_sos = None
        total_pct_producao_pre_impresso = None
    
    total_consumo_total_fmt = f"{total_consumo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if total_consumo_total > 0 else "—"
    total_refugo_producao_total_kg_fmt = f"{total_refugo_producao_total_kg:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if total_refugo_producao_total_kg > 0 else "—"
    total_pct_producao_sos_fmt = f"{total_pct_producao_sos:.2f}".replace(".", ",") + "%" if total_pct_producao_sos is not None else "—"
    total_pct_producao_pre_impresso_fmt = f"{total_pct_producao_pre_impresso:.2f}".replace(".", ",") + "%" if total_pct_producao_pre_impresso is not None else "—"

    # Gerar gráfico comparativo mensal
    chart_image = generate_comparativo_mensal_chart(rows_mensal)

    return render_template(
        "comparativo_mensal.html",
        rows_mensal=rows_mensal,
        meta_quantidade=int(meta_quantidade_padrao),
        total_quantidade_fmt=total_quantidade_fmt,
        total_meta_fmt=total_meta_fmt,
        total_pct_sos_fmt=total_pct_sos_fmt,
        total_pct_sos_flexo_fmt=total_pct_sos_flexo_fmt,
        rows_producao_tipo=rows_producao_tipo,
        total_consumo_total_fmt=total_consumo_total_fmt,
        total_refugo_producao_total_kg_fmt=total_refugo_producao_total_kg_fmt,
        total_pct_producao_sos_fmt=total_pct_producao_sos_fmt,
        total_pct_producao_pre_impresso_fmt=total_pct_producao_pre_impresso_fmt,
        anos_disponiveis=anos_disponiveis,
        ano_selecionado=ano_selecionado,
        action_url=url_for("main.comparativo_mensal"),
        chart_image=chart_image,
    )

# Rota para exibir a análise detalhada em tabelas
@main_bp.route("/analise")
def analise():
    conn = get_db_connection()
    df_all = pd.read_sql_query("SELECT * FROM producao", conn)
    conn.close()
    
    # Prepara o DataFrame original com conversões de data
    if not df_all.empty:
        df_all['data'] = pd.to_datetime(df_all['data'], errors='coerce')
        df_all['data_impressora'] = pd.to_datetime(df_all['data_impressora'], errors='coerce')
        df_all['data_robo'] = pd.to_datetime(df_all['data_robo'], errors='coerce')
        df_all['data_inspecao'] = pd.to_datetime(df_all['data_inspecao'], errors='coerce')
    
    # DataFrame específico para Análise SOS (completamente independente - começa do DataFrame original)
    df_sos_analysis = df_all.copy() if not df_all.empty else pd.DataFrame()
    if not df_sos_analysis.empty:
        # Aplica filtros específicos de SOS (apenas os que começam com 'sos_')
        sos_servico = request.args.get('sos_servico', '').strip()
        if sos_servico:
            df_sos_analysis = df_sos_analysis[df_sos_analysis['servico'].str.contains(sos_servico, case=False, na=False)]
        sos_num_of = request.args.get('sos_num_of', '').strip()
        if sos_num_of:
            df_sos_analysis = df_sos_analysis[df_sos_analysis['num_of'].str.contains(sos_num_of, case=False, na=False)]
        sos_start_date = request.args.get('sos_start_date')
        sos_end_date = request.args.get('sos_end_date')
        if sos_start_date and sos_end_date:
            df_sos_analysis = df_sos_analysis[(df_sos_analysis['data'] >= sos_start_date) & (df_sos_analysis['data'] <= sos_end_date)]
        selected_sos_operadores = request.args.getlist('sos_operadores')
        if selected_sos_operadores:
            df_sos_analysis = df_sos_analysis[df_sos_analysis['operador'].isin(selected_sos_operadores)]
        selected_sos_maquinas = request.args.getlist('sos_maquinas')
        if selected_sos_maquinas:
            df_sos_analysis = df_sos_analysis[df_sos_analysis['sos'].isin(selected_sos_maquinas)]
    
    # DataFrame específico para Análise Impressora (completamente independente - começa do DataFrame original)
    df_impressora_analysis = df_all.copy() if not df_all.empty else pd.DataFrame()
    if not df_impressora_analysis.empty:
        # Aplica filtros específicos de Impressora (apenas os que começam com 'impressora_')
        impressora_servico = request.args.get('impressora_servico', '').strip()
        if impressora_servico:
            df_impressora_analysis = df_impressora_analysis[df_impressora_analysis['servico'].str.contains(impressora_servico, case=False, na=False)]
        impressora_num_of = request.args.get('impressora_num_of', '').strip()
        if impressora_num_of:
            df_impressora_analysis = df_impressora_analysis[df_impressora_analysis['num_of'].str.contains(impressora_num_of, case=False, na=False)]
        impressora_start_date_impressora = request.args.get('impressora_start_date_impressora')
        impressora_end_date_impressora = request.args.get('impressora_end_date_impressora')
        if impressora_start_date_impressora and impressora_end_date_impressora:
            df_impressora_analysis = df_impressora_analysis[(df_impressora_analysis['data_impressora'] >= impressora_start_date_impressora) & (df_impressora_analysis['data_impressora'] <= impressora_end_date_impressora)]
        selected_impressora_operadores = request.args.getlist('impressora_operadores')
        if selected_impressora_operadores:
            df_impressora_analysis = df_impressora_analysis[df_impressora_analysis['operador_impressora'].isin(selected_impressora_operadores)]
    
    # DataFrame base para outras análises (usado apenas para operador SOS quando não há filtros específicos)
    df_base = df_sos_analysis.copy() if not df_sos_analysis.empty else pd.DataFrame()
    df_operator_impressora_final = pd.DataFrame()
    
    # DataFrame específico para Análise por Operador (completamente independente - começa do DataFrame original)
    df_operator_analysis = df_all.copy() if not df_all.empty else pd.DataFrame()
    if not df_operator_analysis.empty:
        # Aplica filtros específicos de operador (apenas os que começam com 'operator_')
        operator_servico = request.args.get('operator_servico', '').strip()
        if operator_servico:
            df_operator_analysis = df_operator_analysis[df_operator_analysis['servico'].str.contains(operator_servico, case=False, na=False)]
        operator_num_of = request.args.get('operator_num_of', '').strip()
        if operator_num_of:
            df_operator_analysis = df_operator_analysis[df_operator_analysis['num_of'].str.contains(operator_num_of, case=False, na=False)]
        operator_start_date = request.args.get('operator_start_date')
        operator_end_date = request.args.get('operator_end_date')
        if operator_start_date and operator_end_date:
            df_operator_analysis['data'] = pd.to_datetime(df_operator_analysis['data'], errors='coerce')
            df_operator_analysis = df_operator_analysis[(df_operator_analysis['data'] >= operator_start_date) & (df_operator_analysis['data'] <= operator_end_date)]
        selected_operator_operadores = request.args.getlist('operator_operadores')
        if selected_operator_operadores:
            df_operator_analysis = df_operator_analysis[df_operator_analysis['operador'].isin(selected_operator_operadores)]
        selected_operator_maquinas = request.args.getlist('operator_maquinas')
        if selected_operator_maquinas:
            df_operator_analysis = df_operator_analysis[df_operator_analysis['sos'].isin(selected_operator_maquinas)]
    
    # DataFrame específico para Análise por Operador Impressora (completamente independente - começa do DataFrame original)
    df_operator_impressora_analysis = df_all.copy() if not df_all.empty else pd.DataFrame()
    if not df_operator_impressora_analysis.empty:
        # Aplica filtros específicos de operador impressora (apenas os que começam com 'operator_impressora_')
        operator_impressora_servico = request.args.get('operator_impressora_servico', '').strip()
        if operator_impressora_servico:
            df_operator_impressora_analysis = df_operator_impressora_analysis[df_operator_impressora_analysis['servico'].str.contains(operator_impressora_servico, case=False, na=False)]
        operator_impressora_num_of = request.args.get('operator_impressora_num_of', '').strip()
        if operator_impressora_num_of:
            df_operator_impressora_analysis = df_operator_impressora_analysis[df_operator_impressora_analysis['num_of'].str.contains(operator_impressora_num_of, case=False, na=False)]
        operator_impressora_start_date_impressora = request.args.get('operator_impressora_start_date_impressora')
        operator_impressora_end_date_impressora = request.args.get('operator_impressora_end_date_impressora')
        if operator_impressora_start_date_impressora and operator_impressora_end_date_impressora:
            df_operator_impressora_analysis['data_impressora'] = pd.to_datetime(df_operator_impressora_analysis['data_impressora'], errors='coerce')
            df_operator_impressora_analysis = df_operator_impressora_analysis[(df_operator_impressora_analysis['data_impressora'] >= operator_impressora_start_date_impressora) & (df_operator_impressora_analysis['data_impressora'] <= operator_impressora_end_date_impressora)]
        selected_operator_impressora_operadores = request.args.getlist('operator_impressora_operadores')
        if selected_operator_impressora_operadores:
            df_operator_impressora_analysis = df_operator_impressora_analysis[df_operator_impressora_analysis['operador_impressora'].isin(selected_operator_impressora_operadores)]
    
    machine_summary, operator_summary, machine_total, operator_total, operator_impressora_summary, operator_impressora_total = [None] * 6
    
    # Função auxiliar para formatar segundos (definida aqui para uso em todas as análises)
    def format_seconds(seconds):
        if pd.isna(seconds) or seconds == 0: return "00:00:00"
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{secs:02}"
    
    if not df_sos_analysis.empty:
        # Calcula colunas auxiliares e agregações para as tabelas
        df_sos_analysis['peso_boas'] = df_sos_analysis['quantidade'] * (df_sos_analysis['milheiro'] / 1000)
        
        # Análise por SOS - usa df_sos_analysis (com filtro de Data SOS)
        machine_summary = df_sos_analysis.groupby('sos').agg(
            media_sacos_p_min=('velocidade_un_min', 'mean'),
            contagem_servico=('id', 'count'),
            media_percentual_refugo=('refugo_pct', 'mean'),
            soma_quant=('quantidade', 'sum'),
            media_tempo_acerto=('tempo_acerto_s', 'mean')
        ).reset_index()
        # Filtra apenas SOS 1, SOS 2 e SOS 3
        machine_summary = machine_summary[machine_summary['sos'].isin(['SOS 1', 'SOS 2', 'SOS 3'])]
        # Filtra apenas SOS 1, SOS 2 e SOS 3 para os cálculos do Total Geral
        df_sos_only = df_sos_analysis[df_sos_analysis['sos'].isin(['SOS 1', 'SOS 2', 'SOS 3'])]
        
        # Percentual consolidado do período (mesmo critério do Comparativo Mensal): refugo_sos / (peso_boas_sos + refugo_sos) × 100
        rsos_kg = (df_sos_only['refugo_acerto_sos'].fillna(0) + df_sos_only['refugo_pre_impresso'].fillna(0) + df_sos_only['refugo_sos'].fillna(0)) if not df_sos_only.empty else pd.Series(dtype=float)
        soma_rsos = rsos_kg.sum() if not df_sos_only.empty else 0
        soma_peso_sos = df_sos_only['peso_boas'].sum() if not df_sos_only.empty else 0
        den_sos = soma_peso_sos + soma_rsos
        media_percentual_refugo_total = (soma_rsos / den_sos * 100) if den_sos > 0 and not df_sos_only.empty else (df_sos_only['refugo_pct'].mean() if not df_sos_only.empty else 0)
        
        refugo_total = df_sos_only['refugo_producao_total'].sum() if not df_sos_only.empty else 0
        peso_boas_total = df_sos_only['peso_boas'].sum() if not df_sos_only.empty else 0
        media_por_maquina = df_sos_only.groupby("sos")["refugo_pct"].mean().reset_index() if not df_sos_only.empty else pd.DataFrame()
        
        # Calcula média de sacos p/ min apenas para SOS 1, SOS 2 e SOS 3
        media_sacos_p_min_total = df_sos_only['velocidade_un_min'].mean() if 'velocidade_un_min' in df_sos_only.columns and not df_sos_only.empty else 0
        
        machine_total = {
            'sos': 'Total Geral',
            'media_sacos_p_min': media_sacos_p_min_total,
            'contagem_servico': df_sos_only['id'].count() if not df_sos_only.empty else 0,
            'media_percentual_refugo': media_percentual_refugo_total,
            'soma_quant': df_sos_only['quantidade'].sum() if not df_sos_only.empty else 0,
            'media_tempo_acerto': None,
        }
        # Análise por Operador SOS - usa df_operator_analysis se houver filtros específicos, senão usa df_base (exclui ILSON)
        # Verifica se há filtros específicos de operador
        has_operator_filters = any([
            request.args.get('operator_servico'),
            request.args.get('operator_num_of'),
            request.args.get('operator_start_date'),
            request.args.get('operator_end_date'),
            request.args.getlist('operator_operadores'),
            request.args.getlist('operator_maquinas')
        ])
        
        df_operator_final = df_operator_analysis if has_operator_filters else df_sos_analysis.copy()
        
        if not df_operator_final.empty:
            # Filtra apenas operadores SOS (remove ILSON, VALDO e outros que não são SOS)
            df_operator_final = df_operator_final[df_operator_final['operador'].isin(OPERADORES_SOS)]
            df_operator_final['peso_boas'] = df_operator_final['quantidade'] * (df_operator_final['milheiro'] / 1000)
            operator_summary = df_operator_final.groupby('operador').agg(
            media_sacos_p_min=('velocidade_un_min', 'mean'),
            contagem_servico=('id', 'count'),
            media_percentual_refugo=('refugo_pct', 'mean'),
            media_total_acerto=('tempo_acerto_s', 'mean')
        ).reset_index()
            # Garante que apenas operadores SOS apareçam nos resultados
            operator_summary = operator_summary[operator_summary['operador'].isin(OPERADORES_SOS)]
            operator_summary['media_total_acerto'] = operator_summary['media_total_acerto'].apply(format_seconds)
        operator_total = {
            'operador': 'Total Geral',
                'media_sacos_p_min': df_operator_final['velocidade_un_min'].mean() if 'velocidade_un_min' in df_operator_final.columns and not df_operator_final.empty else 0,
                'contagem_servico': df_operator_final['id'].count() if not df_operator_final.empty else 0,
                'media_percentual_refugo': df_operator_final['refugo_pct'].mean() if not df_operator_final.empty else 0,
                'media_total_acerto': format_seconds(df_operator_final['tempo_acerto_s'].mean()) if not df_operator_final.empty else "00:00:00"
            }
        machine_summary['media_tempo_acerto'] = machine_summary['media_tempo_acerto'].apply(format_seconds)
        machine_total['media_tempo_acerto'] = format_seconds(df_sos_only['tempo_acerto_s'].mean()) if not df_sos_only.empty else "00:00:00"
        # Análise Impressora - usa df_impressora_analysis (com filtros específicos)
        df_impressora = df_impressora_analysis[df_impressora_analysis['impressora'] == 'IMPRESSORA'] if not df_impressora_analysis.empty else pd.DataFrame()
        impressora_summary = None
        impressora_total = None
        if not df_impressora.empty:
            impressora_summary = df_impressora.groupby('impressora').agg(
                media_sacos_p_min=('velocidade_un_min_flexo', 'mean'),
                contagem_servico=('id', 'count'),
                media_percentual_refugo=('refugo_pct_flexo', 'mean'),
                soma_quant=('quantidade_impressora', 'sum'),
                media_tempo_acerto=('tempo_acerto_impressora', 'mean')
            ).reset_index()
            impressora_summary['media_tempo_acerto'] = impressora_summary['media_tempo_acerto'].apply(format_seconds)
            
            impressora_total = {
                'impressora': 'Total Geral',
                'media_sacos_p_min': df_impressora['velocidade_un_min_flexo'].mean() if 'velocidade_un_min_flexo' in df_impressora.columns and not df_impressora.empty else 0,
                'contagem_servico': df_impressora['id'].count() if not df_impressora.empty else 0,
                'media_percentual_refugo': df_impressora['refugo_pct_flexo'].mean() if not df_impressora.empty else 0,
                'soma_quant': df_impressora['quantidade_impressora'].sum() if not df_impressora.empty else 0,
                'media_tempo_acerto': format_seconds(df_impressora['tempo_acerto_impressora'].mean()) if not df_impressora.empty else "00:00:00",
            }
            impressora_summary = impressora_summary.to_dict('records')
        
        machine_summary = machine_summary.to_dict('records') if machine_summary is not None else []
        operator_summary = operator_summary.to_dict('records') if operator_summary is not None else []
    
    # Função auxiliar para formatar segundos (definida aqui para uso em todas as análises)
    def format_seconds(seconds):
        if pd.isna(seconds) or seconds == 0: return "00:00:00"
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{secs:02}"
    
    # Análise por Operador Impressora - usa df_operator_impressora_analysis se houver filtros específicos
    # Verifica se há filtros específicos de operador impressora
    has_operator_impressora_filters = any([
        request.args.get('operator_impressora_servico'),
        request.args.get('operator_impressora_num_of'),
        request.args.get('operator_impressora_start_date_impressora'),
        request.args.get('operator_impressora_end_date_impressora'),
        request.args.getlist('operator_impressora_operadores')
    ])
    
    # Se não houver filtros específicos, usa df_impressora_analysis como base (já filtrado pelos filtros gerais)
    if has_operator_impressora_filters:
        df_operator_impressora_final = df_operator_impressora_analysis.copy()
    else:
        # Usa df_impressora_analysis se disponível, senão DataFrame vazio
        df_operator_impressora_final = df_impressora_analysis.copy() if not df_impressora_analysis.empty else pd.DataFrame()
    
    if not df_operator_impressora_final.empty:
        # Filtra apenas operadores Impressora e apenas registros com impressora preenchida
        df_operator_impressora_final = df_operator_impressora_final[
            (df_operator_impressora_final['operador_impressora'].isin(OPERADORES_IMPRESSORA)) &
            (df_operator_impressora_final['impressora'] == 'IMPRESSORA')
        ]
        
        if not df_operator_impressora_final.empty:
            operator_impressora_summary = df_operator_impressora_final.groupby('operador_impressora').agg(
                media_sacos_p_min=('velocidade_un_min_flexo', 'mean'),
            contagem_servico=('id', 'count'),
                media_percentual_refugo=('refugo_pct_flexo', 'mean'),
                media_total_acerto=('tempo_acerto_impressora', 'mean')
        ).reset_index()
            operator_impressora_summary.rename(columns={'operador_impressora': 'operador'}, inplace=True)
            operator_impressora_summary['media_total_acerto'] = operator_impressora_summary['media_total_acerto'].apply(format_seconds)
            operator_impressora_total = {
                'operador': 'Total Geral',
                'media_sacos_p_min': df_operator_impressora_final['velocidade_un_min_flexo'].mean() if 'velocidade_un_min_flexo' in df_operator_impressora_final.columns and not df_operator_impressora_final.empty else 0,
                'contagem_servico': df_operator_impressora_final['id'].count() if not df_operator_impressora_final.empty else 0,
                'media_percentual_refugo': df_operator_impressora_final['refugo_pct_flexo'].mean() if not df_operator_impressora_final.empty else 0,
                'media_total_acerto': format_seconds(df_operator_impressora_final['tempo_acerto_impressora'].mean()) if not df_operator_impressora_final.empty else "00:00:00"
            }
            operator_impressora_summary = operator_impressora_summary.to_dict('records') if operator_impressora_summary is not None else []
        else:
            operator_impressora_summary = []
            operator_impressora_total = None
    else:
        operator_impressora_summary = []
        operator_impressora_total = None
    
    return render_template('analise.html', machine_summary=machine_summary, operator_summary=operator_summary, machine_total=machine_total, operator_total=operator_total, impressora_summary=impressora_summary, impressora_total=impressora_total, operator_impressora_summary=operator_impressora_summary, operator_impressora_total=operator_impressora_total, all_operadores=ALL_OPERADORES, all_operadores_sos=OPERADORES_SOS, operadores_impressora=OPERADORES_IMPRESSORA, operadores_sos=OPERADORES_SOS, action_url=url_for('main.analise')) 