"""
Blueprint para rotas de relatórios de custo
"""
from flask import Blueprint, render_template, request, Response
from app.custo.services.relatorio_service import obter_dados_relatorio, exportar_custo_csv

bp = Blueprint("relatorio", __name__)


@bp.route("/custo", methods=["GET"])
def custo():
    """Rota principal para o relatório de custos"""
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    servico = request.args.get("servico")
    num_of = request.args.get("num_of")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    dados, custo_op_un = obter_dados_relatorio(data_inicio, data_fim, servico, num_of, start_date, end_date)

    return render_template("relatorio/index.html",
                         dados=dados,
                         custo_op_un=custo_op_un,
                         ini=(data_inicio or ''),
                         fim=(data_fim or ''))


@bp.route("/exportar_custo")
def exportar_custo():
    """Exporta relatório de custos para CSV"""
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    servico = request.args.get("servico")
    num_of = request.args.get("num_of")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    csv_content = exportar_custo_csv(data_inicio, data_fim, servico, num_of, start_date, end_date)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=custo_producao.csv"}
    )
