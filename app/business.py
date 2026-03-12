from .config import IDEAL_SPEED_RATES, IDEAL_SETUP_TIMES_MIN, IDEAL_SCRAP_RATES_SOS_PCT

# Função auxiliar para converter valores do formulário para float, tratando strings vazias
def safe_float(value, default=0.0):
    """Converte um valor para float, tratando strings vazias e None."""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

# Função auxiliar para converter valores do formulário para int, tratando strings vazias
def safe_int(value, default=0):
    """Converte um valor para int, tratando strings vazias e None."""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# Converte uma string de tempo (HH:MM) para segundos.
def get_seconds_from_time(time_str):
    """Converte uma string de tempo (HH:MM) para segundos."""
    if not time_str:
        return 0
    h, m = map(int, time_str.split(':'))
    return h * 3600 + m * 60

# Calcula as métricas de produção a partir dos dados do formulário
def calcular_metricas_producao(form_data):
    try:
        # Extrai e converte os dados do formulário
        m = safe_float(form_data.get('milheiro', 0))
        # Calcula o refugo total como soma das 5 colunas de refugo
        rf = safe_float(form_data.get('refugo_flexo', 0))
        rpi = safe_float(form_data.get('refugo_pre_impresso', 0))
        rs = safe_float(form_data.get('refugo_sos', 0))
        raf = safe_float(form_data.get('refugo_acerto_flexo', 0))
        ras = safe_float(form_data.get('refugo_acerto_sos', 0))
        peso_unidade = m / 1000 if m > 0 else 0
        refugo_robo = safe_float(form_data.get('refugo_robo', 0))
        refugo_inspecao_final = safe_float(form_data.get('refugo_inspecao_final', 0))
        rsos = rs + ras  # Refugo SOS (soma dos 3 tipos referentes a SOS)
        rflexo = rf + raf + rpi  # Refugo Flexo (soma dos 2 tipos referentes a Flexo)
        r = rf + rpi + rs + raf + ras  # Refugo total (soma em kg dos refugos da produção SOS e Flexo)
        
        qsos = safe_int(form_data.get('quantidade', 0))  # Quantidade SOS
        qflexo = safe_int(form_data.get('quantidade_impressora', 0))  # Quantidade Impressora
        sos = form_data.get('sos', '') or ''
        formato = form_data.get('formato', '') or ''
        papel = form_data.get('papel', '') or ''
        qtd_cliches = safe_int(form_data.get('qtd_cliches', 0))

        # Calcula tempo de produção SOS do dia 1
        tp_sos_dia1 = 0
        inicio_prod = (form_data.get('inicio_prod') or '').strip()
        fim_prod = (form_data.get('fim_prod') or '').strip()
        if inicio_prod and fim_prod:
            inicio_s = get_seconds_from_time(inicio_prod)
            fim_s = get_seconds_from_time(fim_prod)
            tp_sos_dia1 = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600
        # Calcula tempo de produção SOS do dia 2 (se houver)
        tp_sos_dia2 = 0
        inicio_prod_2 = (form_data.get('inicio_prod_2') or '').strip()
        fim_prod_2 = (form_data.get('fim_prod_2') or '').strip()
        if inicio_prod_2 and fim_prod_2:
            inicio_s = get_seconds_from_time(inicio_prod_2)
            fim_s = get_seconds_from_time(fim_prod_2)
            tp_sos_dia2 = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600
        actual_prod_time_sos = tp_sos_dia1 + tp_sos_dia2

        # Calcula tempo de produção Impressora
        actual_prod_time_impressora = 0
        inicio_prod_impressora = (form_data.get('inicio_prod_impressora') or '').strip()
        fim_prod_impressora = (form_data.get('fim_prod_impressora') or '').strip()
        if inicio_prod_impressora and fim_prod_impressora:
            inicio_s = get_seconds_from_time(inicio_prod_impressora)
            fim_s = get_seconds_from_time(fim_prod_impressora)
            actual_prod_time_impressora = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600

        # Calcula tempo de acerto
        actual_setup_time_s = 0
        inicio_acerto = (form_data.get('inicio_acerto') or '').strip()
        fim_acerto = (form_data.get('fim_acerto') or '').strip()
        if inicio_acerto and fim_acerto:
            inicio_s = get_seconds_from_time(inicio_acerto)
            fim_s = get_seconds_from_time(fim_acerto)
            actual_setup_time_s = fim_s - inicio_s if fim_s >= inicio_s else (fim_s - inicio_s) + 24 * 3600

        # Calcula perdas, velocidade, peso e refugo
        perdas_un = ((rsos + rflexo) * 1000) / m if m > 0 else 0
        perdas_total_kg = (peso_unidade * (refugo_robo + refugo_inspecao_final)) + r
        refugo_robo_kg = refugo_robo * peso_unidade
        refugo_inspecao_final_kg = refugo_inspecao_final * peso_unidade
        actual_speed_un_min_sos = (qsos / (actual_prod_time_sos / 60)) if actual_prod_time_sos > 0 else 0
        actual_speed_un_min_flexo = (qflexo / (actual_prod_time_impressora / 60)) if actual_prod_time_impressora > 0 else 0
        kg_por_unidade = m / 1000 if m > 0 else 0
        peso_boas_sos = qsos * kg_por_unidade
        peso_boas_flexo = qflexo * kg_por_unidade
        actual_scrap_pct = (rsos / (peso_boas_sos + rsos)) * 100 if peso_boas_sos > 0 else 0
        actual_scrap_pct_flexo = (rflexo / (peso_boas_flexo + rflexo)) * 100 if peso_boas_flexo > 0 else 0

        # Define velocidade ideal conforme formato (SOS sempre usa formato)
        ideal_speed_un_h = IDEAL_SPEED_RATES.get(formato, 0)
        ideal_speed_un_min = ideal_speed_un_h / 60
        speed_performance = (actual_speed_un_min_sos / ideal_speed_un_min) if actual_speed_un_min_sos > 0 else 0

        # Calcula tempo de acerto ideal e performance
        ideal_setup_time_s = IDEAL_SETUP_TIMES_MIN.get(qtd_cliches, 0) * 60
        setup_performance = (ideal_setup_time_s / actual_setup_time_s) if actual_setup_time_s > 0 else 1

        # Define refugo ideal conforme papel (SOS sempre usa papel)
        ideal_scrap_pct = IDEAL_SCRAP_RATES_SOS_PCT.get(papel, 100.0)
        actual_yield = 100.0 - actual_scrap_pct
        ideal_yield = 100.0 - ideal_scrap_pct
        scrap_performance = (actual_yield / ideal_yield) if ideal_yield > 0 else 0
        # Calcula eficiência total
        total_efficiency = (speed_performance * setup_performance * scrap_performance) * 100
        return {
            "refugo_pct": actual_scrap_pct, "refugo_pct_flexo": actual_scrap_pct_flexo, "eficiencia_pct": total_efficiency,
            "velocidade_un_min": actual_speed_un_min_sos, "velocidade_un_min_flexo": actual_speed_un_min_flexo, "perdas_un": perdas_un,
            "perdas_total_kg": perdas_total_kg, "refugo_robo_kg": refugo_robo_kg, "refugo_inspecao_final_kg": refugo_inspecao_final_kg,
            "tempo_prod_s": actual_prod_time_sos, "tempo_acerto_s": actual_setup_time_s
        }
    except Exception as e:
        # Log do erro para debug (pode ser removido em produção)
        import traceback
        print(f"Erro ao calcular métricas: {e}")
        print(traceback.format_exc())
        # Retorna valores padrão em caso de erro
        return {"refugo_pct": 0, "refugo_pct_flexo": 0, "eficiencia_pct": 0, "velocidade_un_min": 0, "velocidade_un_min_flexo": 0, "perdas_un": 0, "perdas_total_kg": 0, "refugo_robo_kg": 0, "refugo_inspecao_final_kg": 0, "tempo_prod_s": 0, "tempo_acerto_s": 0} 