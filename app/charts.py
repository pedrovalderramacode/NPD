import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Adiciona rótulos de valor às barras ou barras horizontais em um gráfico

def add_labels_to_plot(ax, kind='bar', y_format='{:.2f}'):
    if kind == 'barh':
        for p in ax.patches:
            width = p.get_width()
            ax.annotate(y_format.format(width), (width, p.get_y() + p.get_height() / 2),
                        xytext=(5, 0), textcoords='offset points', va='center', ha='left', fontsize=9, color='#333')
    elif kind == 'bar':
        for p in ax.patches:
            height = p.get_height()
            ax.annotate(y_format.format(height), (p.get_x() + p.get_width() / 2, height),
                        ha='center', va='bottom', fontsize=9, color='#333', xytext=(0, 4), textcoords='offset points')

# Gera um gráfico de dispersão (scatter)
def plot_scatter(df, x_col, y_col, title, xlabel, ylabel):
    if df.empty or len(df) < 2: return None
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = plt.cm.viridis(np.linspace(0, 1, len(df.index)))
    for i, txt in enumerate(df.index):
        ax.scatter(df[x_col].iloc[i], df[y_col].iloc[i], color=colors[i], alpha=0.8, edgecolors='w', s=150, label=txt)
        ax.annotate(txt, (df[x_col].iloc[i], df[y_col].iloc[i]), textcoords="offset points", xytext=(0,15), ha='center', fontsize=9)
    ax.set_title(title, fontsize=14, pad=20, weight='bold')
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.legend(title='Formatos', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    buf = BytesIO(); plt.savefig(buf, format='png', transparent=True); buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# Gera um gráfico combinado de barras e linha
def plot_combo_chart(df, bar_col, line_col, title, bar_label, line_label):
    if df.empty: return None
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.bar(df.index, df[bar_col], color='#3498db', label=bar_label, alpha=0.8)
    ax1.set_ylabel(bar_label, color='#3498db', fontsize=11)
    ax1.tick_params(axis='y', labelcolor='#3498db')
    plt.xticks(rotation=45, ha='right')
    ax2 = ax1.twinx()
    ax2.plot(df.index, df[line_col], color='#e74c3c', marker='o', linestyle='--', label=line_label)
    ax2.set_ylabel(line_label, color='#e74c3c', fontsize=11)
    ax2.tick_params(axis='y', labelcolor='#e74c3c')
    ax1.set_title(title, fontsize=14, pad=20, weight='bold')
    ax1.set_xlabel('Máquina', fontsize=11)
    fig.tight_layout(pad=1.5)
    buf = BytesIO(); plt.savefig(buf, format='png', transparent=True); buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# Gera um gráfico de radar para comparar múltiplas métricas
def plot_radar_chart(df_normalized, title):
    if df_normalized.empty: return None
    labels = df_normalized.columns
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    colors = plt.cm.plasma(np.linspace(0, 1, len(df_normalized.index)))
    for i, (index, row) in enumerate(df_normalized.iterrows()):
        values = row.tolist()
        values += values[:1]
        ax.plot(angles, values, label=index, color=colors[i], linewidth=2)
        ax.fill(angles, values, color=colors[i], alpha=0.25)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=11)
    ax.legend(loc='upper right', bbox_to_anchor=(1.4, 1.1))
    ax.set_title(title, weight='bold', size='large', position=(0.5, 1.15))
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# Gera um gráfico de barras (vertical ou horizontal)
def plot_bar_chart(data, title, xlabel, ylabel, color, y_format, kind='bar'):
    if data.empty: return None
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(8, 5))
    data.plot(kind=kind, ax=ax, color=color, legend=None, width=0.7)
    ax.set_title(title, fontsize=14, pad=20, weight='bold')
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.tick_params(axis='both', which='major', labelsize=10, colors='#666')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#ddd')
    ax.grid(axis='y' if kind != 'barh' else 'x', linestyle='--', alpha=0.6)
    ax.set_axisbelow(True)
    add_labels_to_plot(ax, kind=kind, y_format=y_format)
    if kind == 'barh': ax.tick_params(axis='y', length=0)
    else: ax.tick_params(axis='x', length=0); plt.xticks(rotation=45, ha='right')
    plt.tight_layout(pad=1.5)
    buf = BytesIO(); plt.savefig(buf, format='png', transparent=True); buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# Funções geradoras de gráficos específicos para o dashboard e análise

def generate_operator_performance_radar(df):
    # Gera gráfico de radar de performance do operador
    op_data = df.groupby('operador').agg(
        eficiencia_pct=('eficiencia_pct', 'mean'),
        velocidade_un_min=('velocidade_un_min', 'mean'),
        tempo_acerto_s=('tempo_acerto_s', 'mean'),
        refugo_pct=('refugo_pct', 'mean')
    ).fillna(0)
    if op_data.empty: return None
    op_data['tempo_acerto_inv'] = op_data['tempo_acerto_s'].max() - op_data['tempo_acerto_s']
    op_data['refugo_inv'] = op_data['refugo_pct'].max() - op_data['refugo_pct']
    op_norm = op_data[['eficiencia_pct', 'velocidade_un_min', 'tempo_acerto_inv', 'refugo_inv']]
    op_norm = (op_norm - op_norm.min()) / (op_norm.max() - op_norm.min())
    op_norm.columns = ['Eficiência', 'Velocidade', 'Agilidade (Acerto)', 'Qualidade (Refugo)']
    return plot_radar_chart(op_norm.fillna(0), 'Performance Geral do Operador')

def generate_machine_prod_vs_scrap(df):
    # Gera gráfico combinado de produção vs. refugo por máquina
    machine_data = df.groupby('maquina').agg(
        quantidade=('quantidade', 'sum'),
        refugo_pct=('refugo_pct', 'mean')
    )
    return plot_combo_chart(machine_data, 'quantidade', 'refugo_pct', 
                            'Produção vs. Refugo por Máquina', 'Produção Total (un)', '% Refugo Médio')

def generate_format_eff_vs_scrap(df):
    # Gera gráfico de dispersão eficiência vs. refugo por formato
    format_data = df.groupby('formato').agg(
        eficiencia_pct=('eficiencia_pct', 'mean'),
        refugo_pct=('refugo_pct', 'mean')
    )
    return plot_scatter(format_data, 'refugo_pct', 'eficiencia_pct', 
                        'Eficiência vs. Refugo por Formato', '% Refugo Médio', '% Eficiência Média')

def generate_avg_qty_by_operator(df):
    # Gera gráfico de barras da quantidade média por operador
    data = df.groupby('operador')['quantidade'].mean().sort_values(ascending=False).head(5)
    return plot_bar_chart(data, 'Top 5 Operadores por Quantidade Média', '', 'Quantidade Média (un)', 
                          '#5dade2', '{:,.0f}')

def generate_scrap_by_format(df):
    # Gera gráfico de barras do refugo por formato
    data = df.groupby('formato')['refugo_pct'].mean().sort_values(ascending=False).head(5)
    return plot_bar_chart(data, 'Top 5 Formatos com Maior Refugo', '', '% Refugo', '#e74c3c', '{:.1f}%')

def generate_avg_setup_time_by_op(df):
    # Gera gráfico de barras horizontal do tempo médio de acerto por operador
    df['tempo_acerto_min'] = df['tempo_acerto_s'] / 60
    data = df.groupby('operador')['tempo_acerto_min'].mean().sort_values(ascending=True)
    return plot_bar_chart(data, 'Tempo Médio de Acerto por Operador', 'Minutos', '', '#af7ac5', '{:.1f} min', 'barh')

def generate_un_min_por_maquina(df):
    # Gera gráfico de barras horizontal da velocidade média por máquina
    data = df.groupby('maquina')['velocidade_un_min'].mean().sort_values(ascending=True)
    return plot_bar_chart(data, 'Velocidade Média por Máquina', 'Unidades/Min', '', '#58d68d', '{:.0f}', kind='barh')

def generate_refugo_por_operador(df):
    # Gera gráfico de barras do refugo por operador
    data = df.groupby('operador')['refugo_pct'].mean().sort_values(ascending=False)
    return plot_bar_chart(data, '% Refugo por Operador', '% Refugo', '', '#f5b041', '{:.1f}%')

def generate_comparativo_mensal_chart(rows_mensal):
    """
    Gera gráfico combinado de barras e linhas para comparativo mensal.
    Barras azuis: Quantidade Produzida
    Linha laranja: % Refugo SOS
    Linha cinza: % Refugo SOS + Flexo
    """
    if not rows_mensal or len(rows_mensal) == 0:
        return None
    
    # Preparar dados
    meses = [r['mes_nome'] for r in rows_mensal]
    quantidades = [r['quantidade_mes'] for r in rows_mensal]
    pct_refugo_sos = [r.get('pct_refugo_sos') if r.get('pct_refugo_sos') is not None else None for r in rows_mensal]
    pct_refugo_sos_flexo = [r.get('pct_refugo_sos_flexo') if r.get('pct_refugo_sos_flexo') is not None else None for r in rows_mensal]
    
    # Verificar se há dados para exibir
    if all(q == 0 for q in quantidades) and all(p is None or p == 0 for p in pct_refugo_sos) and all(p is None or p == 0 for p in pct_refugo_sos_flexo):
        return None
    
    # Configurar estilo com fundo cinza escuro (chumbo)
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(14, 8), facecolor='#3d4a5c')
    fig.patch.set_facecolor('#3d4a5c')
    ax1.set_facecolor('#3d4a5c')
    
    # Criar barras azuis médias para quantidade produzida (usar índices numéricos)
    x_positions = range(len(meses))
    bars = ax1.bar(x_positions, quantidades, color='#3498db', alpha=0.9, label='Quantidade Produzida', width=0.6, edgecolor='#2980b9', linewidth=0.8)
    
    # Adicionar valores no topo das barras (texto branco)
    for i, (bar, qty) in enumerate(zip(bars, quantidades)):
        if qty > 0:  # Só mostrar se houver quantidade
            height = bar.get_height()
            ax1.annotate(f'{qty:,.0f}'.replace(',', '.'),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 4),
                        textcoords='offset points',
                        ha='center', va='bottom',
                        fontsize=9, color='white', weight='bold')
    
    # Configurar eixo Y esquerdo (Quantidade) - texto branco/azul claro
    ax1.set_ylabel('QUANTIDADE PRODUZIDA', fontsize=12, color='#5dade2', weight='bold')
    ax1.tick_params(axis='y', labelcolor='#5dade2', labelsize=10)
    ax1.set_xlabel('Meses', fontsize=11, weight='bold', color='white')
    ax1.tick_params(axis='x', labelcolor='white', labelsize=10)
    # Definir limite máximo do eixo Y esquerdo para 1 milhão
    ax1.set_ylim(bottom=0, top=1000000)
    ax1.grid(axis='y', linestyle='--', alpha=0.3, color='#ecf0f1', linewidth=0.8)
    ax1.grid(axis='x', linestyle='--', alpha=0.2, color='#ecf0f1', linewidth=0.5)
    ax1.set_axisbelow(True)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#ecf0f1')
    ax1.spines['bottom'].set_color('#ecf0f1')
    
    # Criar eixo Y direito para porcentagens
    ax2 = ax1.twinx()
    ax2.set_facecolor('#3d4a5c')
    
    # Converter None para 0 para plotagem (mas manter None para não plotar)
    pct_refugo_sos_plot = [p if p is not None else 0 for p in pct_refugo_sos]
    pct_refugo_sos_flexo_plot = [p if p is not None else 0 for p in pct_refugo_sos_flexo]
    
    # Usar índices numéricos para plotar as linhas (meses são strings, precisamos de índices)
    x_positions = range(len(meses))
    
    # Linha laranja vibrante para % Refugo SOS
    line1 = ax2.plot(x_positions, pct_refugo_sos_plot, color='#ff8c00', marker='o', linestyle='-', 
                     linewidth=2.5, markersize=7, label='Média de PERCENTUAL REFUGO SOS', alpha=0.95, markerfacecolor='#ff8c00', markeredgecolor='white', markeredgewidth=1.5)
    
    # Linha cinza claro para % Refugo SOS + Flexo
    line2 = ax2.plot(x_positions, pct_refugo_sos_flexo_plot, color='#bdc3c7', marker='s', linestyle='-', 
                     linewidth=2.5, markersize=7, label='Média de % Refugo SOS + Refugo Flexografica versos Produção das SOS\'s', alpha=0.95, markerfacecolor='#bdc3c7', markeredgecolor='white', markeredgewidth=1.5)
    
    # Adicionar valores nos pontos das linhas (texto branco)
    for i, (mes, pct_sos, pct_flexo) in enumerate(zip(meses, pct_refugo_sos, pct_refugo_sos_flexo)):
        if pct_sos is not None and pct_sos > 0:
            ax2.annotate(f'{pct_sos:.2f}%',
                        xy=(i, pct_sos),
                        xytext=(0, 8),
                        textcoords='offset points',
                        ha='center', va='bottom',
                        fontsize=8, color='white', weight='bold')
        if pct_flexo is not None and pct_flexo > 0:
            ax2.annotate(f'{pct_flexo:.2f}%',
                        xy=(i, pct_flexo),
                        xytext=(0, -12),
                        textcoords='offset points',
                        ha='center', va='top',
                        fontsize=8, color='white', weight='bold')
    
    # Configurar eixo Y direito (% Refugo) - texto branco/cinza claro
    ax2.set_ylabel('% DE REFUGO', fontsize=12, color='#bdc3c7', weight='bold')
    ax2.tick_params(axis='y', labelcolor='#bdc3c7', labelsize=10)
    ax2.set_ylim(bottom=0)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_color('#ecf0f1')
    
    # Título do gráfico (texto branco)
    ax1.set_title('Quantidade Produzida e Porcentagem de Refugo', fontsize=16, pad=20, weight='bold', color='white')
    
    # Garantir que todos os meses apareçam no eixo X
    ax1.set_xticks(range(len(meses)))
    ax1.set_xticklabels(meses, rotation=0, ha='center')
    
    # Legenda combinada - posicionada embaixo do gráfico, centralizada (fundo escuro, texto branco)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    # Usar fig.legend para colocar a legenda fora da área de plotagem, embaixo (mais próxima)
    legend = fig.legend(lines1 + lines2, labels1 + labels2, 
               loc='lower center', ncol=3, fontsize=10, framealpha=0.95, 
               bbox_to_anchor=(0.5, -0.02), frameon=True, fancybox=True, shadow=True,
               facecolor='#3d4a5c', edgecolor='#ecf0f1')
    # Definir cor do texto da legenda como branco
    for text in legend.get_texts():
        text.set_color('white')
    
    # Ajustar layout para dar espaço à legenda embaixo (menos espaço)
    plt.tight_layout(rect=[0, 0.02, 1, 0.98], pad=2.0)
    
    # Converter para base64
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#3d4a5c', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8') 