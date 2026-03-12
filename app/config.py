# Configurações globais e constantes do sistema
import os

# Dicionário com velocidades ideais por formato
IDEAL_SPEED_RATES = {
    '18X30X10': 4100, '22X30X12': 4100, '22X40X12': 3900, '32X30X12': 4000,
    '32X40X12': 3600, '35X45X14': 3200, '32X45X12': 3200, '32X30X16': 3300,
    '28X31X20': 3200, '32X45X16': 3200, '25X30X9': 3900,  '18X25X10': 4100,
    '25X25X9': 3700,  '29X40X15': 3700, '25X40X14': 3900, '25X30X14': 4000,
    '40X45X14': 3000, '31X31X18': 3700, '31X31X16': 3700
}
# Tempo ideal de acerto por quantidade de clichês
IDEAL_SETUP_TIMES_MIN = {1: 15.0, 2: 22.5, 3: 32.5}
# Refugo ideal por tipo de papel
IDEAL_SCRAP_RATES_SOS_PCT = {
    'BRANCO 110G': 8.0, 'BAG 100GRS': 6.0, 'BAG 80GRS': 6.0,
    'BAG 70GRS': 8.0, 'COLLEY 100G': 8.0, 'ECO 70GRS': 10.0,
    'MONOL 70GRS': 10.0
}
# Lista de operadores por categoria
OPERADORES_SOS = sorted(['JOSÉ', 'JOÃO', 'WELLINGTON', 'JULIO', 'LUCAS', 'WILLIAM', 'BETO'])
OPERADORES_IMPRESSORA = sorted(['ILSON'])
OPERADORES_ROBO = sorted(['VALDO'])

# Lista unificada de todos os operadores (para compatibilidade)
ALL_OPERADORES = sorted(OPERADORES_SOS + OPERADORES_IMPRESSORA + OPERADORES_ROBO)
# Lista de máquinas disponíveis
ALL_MAQUINAS = sorted(['IMPRESSORA', 'SOS 1', 'SOS 2', 'SOS 3', 'APLA-2R', 'TROCA MAQ1', 'TROCA MAQ2', 'TROCA MAQ3'])

# Caminho do banco de dados (sempre do diretório local)
DB_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados_producao.db')

# Porta do servidor (8082; 8080/8081 ja em uso no servidor; 5000 nao funciona)
SERVER_PORT = 8082