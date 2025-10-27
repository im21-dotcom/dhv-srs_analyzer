import streamlit as st
import tempfile
import math

# ------------------------- Funções auxiliares -------------------------
# bloco de código para coleta de dados

def extrair_volume_dose_100(filepath):
    return extrair_volume_para_dose_relativa(filepath, alvo_dose=100.0)

def extrair_volume_dose_50(filepath):
    return extrair_volume_para_dose_relativa(filepath, alvo_dose=50.0)

def extrair_volume_dose_10gy(filepath):
    return extrair_volume_para_dose_absoluta(filepath, alvo_dose_cgy=1000.0)

def extrair_volume_dose_12gy(filepath):
    return extrair_volume_para_dose_absoluta(filepath, alvo_dose_cgy=1200.0)

def extrair_volume_dose_18gy(filepath):
    return extrair_volume_para_dose_absoluta(filepath, alvo_dose_cgy=1800.0)

def extrair_volume_dose_20gy(filepath):
    return extrair_volume_para_dose_absoluta(filepath, alvo_dose_cgy=2000.0)

def extrair_volume_dose_25gy(filepath):
    return extrair_volume_para_dose_absoluta(filepath, alvo_dose_cgy=2500.0)

def extrair_volume_dose_30gy(filepath):
    return extrair_volume_para_dose_absoluta(filepath, alvo_dose_cgy=3000.0)

def extrair_volume_ptv(filepath):
    return extrair_volume_por_estrutura(filepath, estrutura_alvo=nome_ptv.strip().lower())

def extrair_volume_overlap(filepath):
    return extrair_volume_por_estrutura(filepath, estrutura_alvo=nome_overlap.strip().lower())

def extrair_dose_max_body(filepath):
    return extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo=nome_body.strip().lower(), chave="dose máx")

# Novas funções para PTV (mín/máx)
def extrair_dose_max_ptv(filepath):
    return extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo=nome_ptv.strip().lower(), chave="dose máx")

def extrair_dose_min_ptv(filepath):
    return extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo=nome_ptv.strip().lower(), chave="dose mín")


def extrair_dose_prescricao(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            if linha.lower().strip().startswith("dose total"):
                try:
                    valor = linha.split(":", 1)[-1].strip().replace(',', '.')
                    return float(valor)
                except ValueError:
                    return None
    return None


def extrair_volume_por_estrutura(filepath, estrutura_alvo):
    return extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo=estrutura_alvo, chave="volume")


def extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo, chave):
    coletando_dados = False

    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            linha_limpa = linha.strip().lower()

            if linha_limpa.startswith("estrutura:"):
                nome_estrutura = linha_limpa.split(":", 1)[-1].strip().lower()
                coletando_dados = (nome_estrutura == estrutura_alvo.strip().lower())
                continue

            if not coletando_dados:
                continue

            if linha_limpa.startswith(chave.lower()):
                try:
                    valor_str = linha.split(":", 1)[-1].strip().replace(',', '.')
                    return float(valor_str)
                except ValueError:
                    continue

    return None


def extrair_volume_para_dose_relativa(filepath, alvo_dose):
    return _extrair_volume_por_coluna(filepath, alvo_dose, coluna="relativa")


def extrair_volume_para_dose_absoluta(filepath, alvo_dose_cgy):
    return _extrair_volume_por_coluna(filepath, alvo_dose_cgy, coluna="absoluta")


def _extrair_volume_por_coluna(filepath, alvo_dose, coluna="relativa"):
    estrutura_alvo = nome_body.lower()
    coletando_dados = False
    dentro_da_tabela = False
    melhor_aproximacao = None
    menor_diferenca = float('inf')

    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            linha_limpa = linha.strip()

            if linha_limpa.lower().startswith("estrutura:"):
                nome_estrutura = linha_limpa.split(":", 1)[-1].strip().lower()
                coletando_dados = (nome_estrutura == estrutura_alvo)
                dentro_da_tabela = False
                continue

            if not coletando_dados:
                continue

            if "Dose relativa [%]" in linha and "Volume da estrutura" in linha:
                dentro_da_tabela = True
                continue

            if not dentro_da_tabela:
                continue

            partes = linha_limpa.split()
            if len(partes) != 3:
                continue

            try:
                dose = float(partes[0].replace(',', '.')) if coluna == "absoluta" else float(partes[1].replace(',', '.'))
                volume = float(partes[2].replace(',', '.'))
            except ValueError:
                continue

            if dose == alvo_dose:
                return volume

            if dose > alvo_dose:
                diferenca = dose - alvo_dose
                if diferenca < menor_diferenca:
                    menor_diferenca = diferenca
                    melhor_aproximacao = volume

    return melhor_aproximacao


# Nova função: extrair dose que cobre X% do volume do PTV
# pct em 0-1 (ex.: 0.02 para 2%)
def extrair_dose_cobrindo_pct_ptv(filepath, pct, volume_ptv):
    if volume_ptv is None:
        return None

    alvo_volume = pct * volume_ptv
    coletando_dados = False
    dentro_da_tabela = False
    rows = []  # tuplas (dose_cgy, volume_cm3)

    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            linha_limpa = linha.strip()

            if linha_limpa.lower().startswith("estrutura:"):
                nome_estrutura = linha_limpa.split(":", 1)[-1].strip().lower()
                coletando_dados = (nome_estrutura == nome_ptv.strip().lower())
                dentro_da_tabela = False
                continue

            if not coletando_dados:
                continue

            if "Dose relativa [%]" in linha and "Volume da estrutura" in linha:
                dentro_da_tabela = True
                continue

            if not dentro_da_tabela:
                continue

            partes = linha_limpa.split()
            if len(partes) != 3:
                continue

            try:
                dose_cgy = float(partes[0].replace(',', '.'))
                volumen = float(partes[2].replace(',', '.'))
            except ValueError:
                continue

            rows.append((dose_cgy, volumen))

    if not rows:
        return None

    # Procurar a maior volume <= alvo_volume (imediatamente inferior)
    candidatos = [r for r in rows if r[1] <= alvo_volume]
    if candidatos:
        # escolher o que tiver maior volume (mais próximo por baixo)
        candidato = max(candidatos, key=lambda x: x[1])
        return candidato[0]

    # Se não houver volume <= alvo (ex.: alvo muito pequeno), escolher o menor volume disponível (maior dose)
    menor = min(rows, key=lambda x: x[1])
    return menor[0]


def extrair_dose_media_ptv(filepath):
    """Extrai a dose média [cGy] da estrutura PTV."""
    coletando_dados = False
    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            linha_limpa = linha.strip().lower()
            if linha_limpa.startswith("estrutura:"):
                nome = linha_limpa.split(":", 1)[-1].strip()
                coletando_dados = (nome.lower() == nome_ptv.strip().lower())
                continue
            if coletando_dados and linha_limpa.startswith("dose média [cgy]:"):
                try:
                    valor = linha.split(":", 1)[-1].strip().replace(",", ".")
                    return float(valor)
                except ValueError:
                    return None
    return None


def extrair_std_ptv(filepath):
    """Extrai o desvio-padrão [cGy] (STD) da estrutura PTV."""
    coletando_dados = False
    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            linha_limpa = linha.strip().lower()
            if linha_limpa.startswith("estrutura:"):
                nome = linha_limpa.split(":", 1)[-1].strip()
                coletando_dados = (nome.lower() == nome_ptv.strip().lower())
                continue
            if coletando_dados and linha_limpa.startswith("std [cgy]:"):
                try:
                    valor = linha.split(":", 1)[-1].strip().replace(",", ".")
                    return float(valor)
                except ValueError:
                    return None
    return None

def extrair_dose_media_iso50(filepath):
    """Extrai a dose média [cGy] da estrutura Dose 50[%]."""
    coletando_dados = False
    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            linha_limpa = linha.strip().lower()
            if linha_limpa.startswith("estrutura:"):
                nome = linha_limpa.split(":", 1)[-1].strip()
                coletando_dados = (nome.lower() == nome_iso50.strip().lower())
                continue
            if coletando_dados and linha_limpa.startswith("dose média [cgy]:"):
                try:
                    valor = linha.split(":", 1)[-1].strip().replace(",", ".")
                    return float(valor)
                except ValueError:
                    return None
    return None

def calcular_v20gy_pulmao(filepath, nome_pulmao):
    """
    Calcula o percentual do volume do pulmão que recebe acima de 20 Gy (V20Gy)
    e retorna também o volume absoluto (cm³), com alta precisão.
    """

    volume_total = None
    volume_acima_20gy = None
    coletando_dados = False
    dentro_tabela = False

    with open(filepath, 'r', encoding='utf-8') as file:
        for linha in file:
            linha_limpa = linha.strip()

            # Detecta início do bloco da estrutura Pulmão
            if linha_limpa.lower().startswith("estrutura:"):
                nome = linha_limpa.split(":", 1)[-1].strip().lower()
                coletando_dados = (nome == nome_pulmao.strip().lower())
                dentro_tabela = False
                continue

            if not coletando_dados:
                continue

            # Detecta início da tabela de DVH
            if "Dose relativa [%]" in linha and "Volume da estrutura" in linha:
                dentro_tabela = True
                continue

            if not dentro_tabela:
                # Coleta volume total do pulmão
                if "volume [cm³]:" in linha_limpa.lower() and volume_total is None:
                    try:
                        valor = linha.split(":", 1)[-1].strip().replace(",", ".")
                        volume_total = float(valor)
                    except ValueError:
                        pass
                continue

            # Tenta ler linhas de dados da tabela (dose, dose relativa, volume)
            partes = linha_limpa.split()
            if len(partes) < 3:
                continue

            try:
                dose_cgy = float(partes[0].replace(",", "."))
                volume = float(partes[2].replace(",", "."))
            except ValueError:
                continue

            # Usa comparação numérica com tolerância para evitar erros de formatação
            if abs(dose_cgy - 2000.0) < 0.05:  # tolerância de 0.05 cGy
                volume_acima_20gy = volume
                break  # encontramos a linha exata, não precisamos continuar

    if volume_total is not None and volume_acima_20gy is not None:
        v20gy = (volume_acima_20gy / volume_total) * 100
        return v20gy, volume_acima_20gy
    else:
        return None, None


# bloco de código para o cálculo das métricas IC,IG,IH e Paddick e demais métricas pedidas

def calcular_metricas_avancadas(dose_prescricao, dose_max_body, dose_max_ptv, dose_min_ptv,
                                 volume_ptv, volume_overlap, volume_iso100, volume_iso50,
                                 d2_ptv, d5_ptv, d95_ptv, d98_ptv,
                                 dose_media_ptv=None, dose_std_ptv=None, dose_media_iso50=None):
    metricas = {}

    # Índice de Conformidade (CI1)
    if volume_ptv and volume_iso100:
        metricas['CI1 (isodose100/PTV)'] = volume_iso100 / volume_ptv
    else:
        metricas['CI1 (isodose100/PTV)'] = None

    # CI2 = Overlap / isodose100
    if volume_overlap is not None and volume_iso100:
        metricas['CI2 (Overlap/isodose100)'] = volume_overlap / volume_iso100
    else:
        metricas['CI2 (Overlap/isodose100)'] = None

    # CI3 = Overlap / PTV
    if volume_overlap is not None and volume_ptv:
        metricas['CI3 (Overlap/PTV)'] = volume_overlap / volume_ptv
    else:
        metricas['CI3 (Overlap/PTV)'] = None

    # CI4 (Paddick) = CI2 * CI3
    ci2 = metricas.get('CI2 (Overlap/isodose100)')
    ci3 = metricas.get('CI3 (Overlap/PTV)')
    if ci2 is not None and ci3 is not None:
        metricas['CI4 (Paddick)'] = ci2 * ci3
    else:
        metricas['CI4 (Paddick)'] = None

    # Índices de Gradiente
    if volume_iso50 and volume_iso100:
        metricas['GI1 (isodose50/isodose100)'] = volume_iso50 / volume_iso100
    else:
        metricas['GI1 (isodose50/isodose100)'] = None

    # Raios efetivos
    try:
        r_iso100 = ((3 * volume_iso100) / (4 * math.pi)) ** (1.0 / 3.0) if volume_iso100 else None
        r_iso50 = ((3 * volume_iso50) / (4 * math.pi)) ** (1.0 / 3.0) if volume_iso50 else None

        # GI2 = raio50 / raio100
        if r_iso50 is not None and r_iso100 is not None:
            metricas['GI2 (raio50/raio100)'] = r_iso50 / r_iso100
        else:
            metricas['GI2 (raio50/raio100)'] = None
            
    except Exception:
        metricas['Raio efetivo isodose100 (cm)'] = None
        metricas['Raio efetivo isodose50 (cm)'] = None
        metricas['GI2 (raio50/raio100)'] = None

    # GI3 = volume isodose50 / volume PTV
    if volume_iso50 and volume_ptv:
        metricas['GI3 (isodose50/PTV)'] = volume_iso50 / volume_ptv
    else:
        metricas['GI3 (isodose50/PTV)'] = None

    # Índices de Homogeneidade
    if dose_max_ptv is not None and dose_min_ptv is not None and dose_min_ptv != 0:
        metricas['HI1 (Dmax_PTV/Dmin_PTV)'] = dose_max_ptv / dose_min_ptv
    else:
        metricas['HI1 (Dmax_PTV/Dmin_PTV)'] = None

    if dose_max_ptv is not None and dose_prescricao is not None and dose_prescricao != 0:
        metricas['HI2 (Dmax_PTV/D_prescricao)'] = dose_max_ptv / dose_prescricao
    else:
        metricas['HI2 (Dmax_PTV/D_prescricao)'] = None

    # HI3 = (D2 - D98) / D_prescricao
    if d2_ptv is not None and d98_ptv is not None and dose_prescricao is not None and dose_prescricao != 0:
        metricas['HI3 ((D2-D98)/D_prescricao)'] = (d2_ptv - d98_ptv) / dose_prescricao
    else:
        metricas['HI3 ((D2-D98)/D_prescricao)'] = None

    # HI4 = (D5 - D95) / D_prescricao
    if d5_ptv is not None and d95_ptv is not None and dose_prescricao is not None and dose_prescricao != 0:
        metricas['HI4 ((D5-D95)/D_prescricao)'] = (d5_ptv - d95_ptv) / dose_prescricao
    else:
        metricas['HI4 ((D5-D95)/D_prescricao)'] = None

    # HI5 (S-index) = (STD_PTV / Dose_prescricao) * 100
    # e Dose média PTV (%) = (Dose_média_PTV / Dose_prescricao) * 100
    if dose_std_ptv is not None and dose_prescricao:
        metricas['HI5 (S-índex)'] = (dose_std_ptv / dose_prescricao) * 100
    else:
        metricas['HI5 (S-índex)'] = None
    
    if dose_media_ptv is not None and dose_prescricao:
        metricas['Dose média PTV (%)'] = (dose_media_ptv / dose_prescricao) * 100
    else:
        metricas['Dose média PTV (%)'] = None

    # Índice de Eficiência Global (Gn)
    if (
        dose_media_ptv is not None and volume_ptv is not None
        and dose_media_iso50 is not None and volume_iso50 is not None
        and dose_media_iso50 != 0 and volume_iso50 != 0
    ):
        metricas['Gn (Dose integral[PTV]/Dose integral[V50%])'] = (
            (dose_media_ptv * volume_ptv) / (dose_media_iso50 * volume_iso50)
        )
    else:
        metricas['Gn (Dose integral[PTV]/Dose integral[V50%])'] = None
    
    return metricas


def imprimir_metricas(metricas):
    print("\n📈 Métricas Calculadas:")
    for nome, valor in metricas.items():
        if valor is not None:
            if 'Raio efetivo' not in nome:
                try:
                    st.write(f"🔹 {nome}: {valor:.4f}")
                except Exception:
                    st.write(f"🔹 {nome}: {valor}")
        else:
            st.write(f"🔹 {nome}: não calculado (dados insuficientes)")

# bloco de código para coleta de métricas de volumes de dose associadas ao desenvolvimento de radionecrose

def imprimir_metricas_por_fracao(n_fracoes, volume_10gy=None, volume_12gy=None,
                                  volume_18gy=None, volume_20gy=None,
                                  volume_25gy=None, volume_30gy=None):
    print("\n📦 Volumes de Dose associados ao desenvolvimento de radionecrose:")

    if n_fracoes == 1:
        print("🔹 Fracionamento: 1 seção de tratamento")
        if volume_10gy is not None:
            print(f"   - Volume de Dose > 10 Gy: {volume_10gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 10 Gy: não encontrado")
        if volume_12gy is not None:
            print(f"   - Volume de Dose > 12 Gy: {volume_12gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 12 Gy: não encontrado")

    elif n_fracoes == 3:
        print("🔹 Fracionamento: 3 seções de tratamento")
        if volume_18gy is not None:
            print(f"   - Volume de Dose > 18 Gy: {volume_18gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 18 Gy: não encontrado")
        if volume_20gy is not None:
            print(f"   - Volume de Dose > 20 Gy: {volume_20gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 20 Gy: não encontrado")

    elif n_fracoes == 5:
        print("🔹 Fracionamento: 5 seções de tratamento")
        if volume_25gy is not None:
            print(f"   - Volume de Dose > 25 Gy: {volume_25gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 25 Gy: não encontrado")
        if volume_30gy is not None:
            print(f"   - Volume de Dose > 30 Gy: {volume_30gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 30 Gy: não encontrado")

    else:
        print("❗ Número de frações inválido. Use 1, 3 ou 5.")

# ------------------------- Interface Streamlit -------------------------
st.title("Análise de DVH - Radioterapia")

# Tipo de tratamento
st.sidebar.header("Configuração do Caso")
tipo_tratamento = st.sidebar.selectbox(
    "Selecione o tipo de tratamento:",
    ["SRS (Radiocirurgia)", "SBRT de Pulmão", "SBRT de Próstata"]
)

st.write("### Nome das estruturas no DVH")
nome_ptv = st.text_input("Qual o nome da sua estrutura de PTV no DVH:", "PTV")
nome_body = st.text_input("Qual o nome da sua estrutura de Corpo no DVH:", "Body")
nome_overlap = st.text_input("Qual o nome da sua estrutura de Interseção do PTV com a Isodose de Prescrição no DVH:", "Overlap")
nome_iso50 = st.text_input("Qual o nome da sua estrutura de Isodose de 50% no DVH:", "Dose 50[%]")

# Nome da estrutura de Pulmão (para SBRT de Pulmão)
if tipo_tratamento == "SBRT de Pulmão":
    nome_pulmao = st.text_input("Qual o nome da sua estrutura de Pulmão no DVH:", "Pulmao")
else:
    nome_pulmao = None

st.sidebar.header("Upload do Arquivo")
uploaded_file = st.sidebar.file_uploader("Envie o arquivo .txt do DVH", type="txt")

if uploaded_file is not None:
    # Salvar temporariamente o arquivo para leitura
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        caminho = tmp.name

    st.success("✅ Arquivo carregado com sucesso!")

    # Mostrar seletor de frações apenas se for SRS
    if tipo_tratamento == "SRS (Radiocirurgia)":
        n_frações = st.sidebar.selectbox("Selecione o número de frações:", [1, 3, 5])
    else:
        n_frações = None  # para SBRT não usamos isso

    # Coletas
    dose_prescricao = extrair_dose_prescricao(caminho)
    dose_max_body = extrair_dose_max_body(caminho)
    dose_max_ptv = extrair_dose_max_ptv(caminho)
    dose_min_ptv = extrair_dose_min_ptv(caminho)
    dose_media_ptv = extrair_dose_media_ptv(caminho)
    dose_std_ptv = extrair_std_ptv(caminho)
    dose_media_iso50 = extrair_dose_media_iso50(caminho)
    volume_ptv = extrair_volume_ptv(caminho)
    volume_overlap = extrair_volume_overlap(caminho)
    volume_iso100 = extrair_volume_dose_100(caminho)
    volume_iso50 = extrair_volume_dose_50(caminho)
    volume_10gy = extrair_volume_dose_10gy(caminho)
    volume_12gy = extrair_volume_dose_12gy(caminho)
    volume_18gy = extrair_volume_dose_18gy(caminho)
    volume_20gy = extrair_volume_dose_20gy(caminho)
    volume_25gy = extrair_volume_dose_25gy(caminho)
    volume_30gy = extrair_volume_dose_30gy(caminho)

    # Doses que cobrem X% do PTV (em cGy)
    d2_ptv = extrair_dose_cobrindo_pct_ptv(caminho, 0.02, volume_ptv)
    d5_ptv = extrair_dose_cobrindo_pct_ptv(caminho, 0.05, volume_ptv)
    d95_ptv = extrair_dose_cobrindo_pct_ptv(caminho, 0.95, volume_ptv)
    d98_ptv = extrair_dose_cobrindo_pct_ptv(caminho, 0.98, volume_ptv)

    # Métricas principais (estendidas)
    metricas = calcular_metricas_avancadas(
        dose_prescricao, dose_max_body, dose_max_ptv, dose_min_ptv,
        volume_ptv, volume_overlap, volume_iso100, volume_iso50,
        d2_ptv, d5_ptv, d95_ptv, d98_ptv,
        dose_media_ptv, dose_std_ptv, dose_media_iso50
    )

    # --- Cálculo do V20Gy do Pulmão (somente para SBRT de Pulmão) ---
    if tipo_tratamento == "SBRT de Pulmão" and nome_pulmao:
        v20gy_pulmao, volume_pulmao_20gy = calcular_v20gy_pulmao(caminho, nome_pulmao)
    else:
        v20gy_pulmao, volume_pulmao_20gy = None, None
    
    # Impressão das métricas organizadas por blocos com valores ideais
    st.subheader("📈 Métricas Calculadas")
    
    # Dicionário de valores ideais
    valores_ideais = {
        'CI1 (isodose100/PTV)': 1,
        'CI2 (Overlap/isodose100)': 1,
        'CI3 (Overlap/PTV)': 1,
        'CI4 (Paddick)': 1,
        'HI1 (Dmax_PTV/Dmin_PTV)': 1,
        'HI2 (Dmax_PTV/D_prescricao)': 1,
        'HI3 ((D2-D98)/D_prescricao)': 0,
        'HI4 ((D5-D95)/D_prescricao)': 0,
        'Gn (Dose integral[PTV]/Dose integral[V50%])': 1,
    }
    
    # Blocos de índices
    blocos = {
        "🔹 Índices de Conformidade": [
            'CI1 (isodose100/PTV)',
            'CI2 (Overlap/isodose100)',
            'CI3 (Overlap/PTV)',
            'CI4 (Paddick)'
        ],
        "🔹 Índices de Homogeneidade": [
            'HI1 (Dmax_PTV/Dmin_PTV)',
            'HI2 (Dmax_PTV/D_prescricao)',
            'HI3 ((D2-D98)/D_prescricao)',
            'HI4 ((D5-D95)/D_prescricao)',
            'HI5 (S-índex)'
        ],
        "🔹 Índices de Gradiente": [
            'GI1 (isodose50/isodose100)',
            'GI2 (raio50/raio100)',
            'GI3 (isodose50/PTV)'
        ],
        "🔹 Índice de Eficiência Global": [
            'Gn (Dose integral[PTV]/Dose integral[V50%])'
        ]
    }
    
    # Impressão formatada
    for bloco_nome, lista_metricas in blocos.items():
        st.markdown(f"### {bloco_nome}")
        bloco_incompleto = False
    
        for nome in lista_metricas:
            valor = metricas.get(nome)
            if valor is not None:
                if nome == 'HI5 (S-índex)':
                    dose_media_norm = metricas.get('Dose média PTV (%)')
                    if dose_media_norm is not None:
                        st.write(f"• {nome}: {valor:.3f}%, associado a uma dose média de {dose_media_norm:.2f}%.")
                    else:
                        st.write(f"• {nome}: {valor:.3f}%")
                    continue
                if nome in valores_ideais:
                    st.write(f"• {nome}: {valor:.4f}; valor ideal = {valores_ideais[nome]}.")
                else:
                    st.write(f"• {nome}: {valor:.4f}")
            else:
                st.write(f"• {nome}: não calculado (dados insuficientes)")
                bloco_incompleto = True
    
        if bloco_incompleto:
            st.warning("⚠️ Verifique o nome das estruturas e o formato do DVH.")

    # Impressão por fração — apenas para SRS
    if tipo_tratamento == "SRS (Radiocirurgia)":   
        st.subheader("📦 Volumes de Dose associados ao desenvolvimento de radionecrose")
        
        if n_frações == 1:
            st.write("🔹 Fracionamento: 1 seção de tratamento")
            st.write(f"   - Volume de Dose > 10 Gy: {volume_10gy:.2f} cm³" if volume_10gy else "   - Volume de Dose > 10 Gy: não encontrado")
            st.write(f"   - Volume de Dose > 12 Gy: {volume_12gy:.2f} cm³" if volume_12gy else "   - Volume de Dose > 12 Gy: não encontrado")
    
        elif n_frações == 3:
            st.write("🔹 Fracionamento: 3 seções de tratamento")
            st.write(f"   - Volume de Dose > 18 Gy: {volume_18gy:.2f} cm³" if volume_18gy else "   - Volume de Dose > 18 Gy: não encontrado")
            st.write(f"   - Volume de Dose > 20 Gy: {volume_20gy:.2f} cm³" if volume_20gy else "   - Volume de Dose > 20 Gy: não encontrado")
    
        elif n_frações == 5:
            st.write("🔹 Fracionamento: 5 seções de tratamento")
            st.write(f"   - Volume de Dose > 25 Gy: {volume_25gy:.2f} cm³" if volume_25gy else "   - Volume de Dose > 25 Gy: não encontrado")
            st.write(f"   - Volume de Dose > 30 Gy: {volume_30gy:.2f} cm³" if volume_30gy else "   - Volume de Dose > 30 Gy: não encontrado")

    # Bloco V20Gy do Pulmão (somente para SBRT de Pulmão)
    if tipo_tratamento == "SBRT de Pulmão":
        st.subheader("📦 Porcentagem do pulmão recebendo acima de 20Gy (V20Gy)")
        if v20gy_pulmao is not None:
            st.write(f"• V20Gy do Pulmão = {v20gy_pulmao:.2f}%")
        else:
            st.write("• V20Gy do Pulmão = não calculado (dados insuficientes)")
    
    # Impressão opcional dos volumes
    if st.checkbox("Deseja ver todos os dados coletados?"):
        st.subheader("📊 Resumo dos volumes e doses utilizados")

        def mostrar_volume(rotulo, valor):
            if valor is not None:
                st.write(f"🔹 {rotulo}: {valor:.2f} cm³")
            else:
                st.write(f"🔹 {rotulo}: não encontrado")

        def mostrar_valor(rotulo, valor):
            if valor is not None:
                st.write(f"🔹 {rotulo}: {valor:.2f} cGy")
            else:
                st.write(f"🔹 {rotulo}: não encontrado")

        mostrar_valor("Dose de prescrição", dose_prescricao)
        mostrar_valor("Dose máxima na estrutura Body (cGy)", dose_max_body)
        mostrar_valor("Dose máxima no PTV (cGy)", dose_max_ptv)
        mostrar_valor("Dose mínima no PTV (cGy)", dose_min_ptv)
        mostrar_valor("Dose média no PTV (cGy)", dose_media_ptv)
        mostrar_valor("Desvio-padrão no PTV (cGy)", dose_std_ptv)
        mostrar_valor("Dose que cobre 2% do PTV (cGy)", d2_ptv)
        mostrar_valor("Dose que cobre 5% do PTV (cGy)", d5_ptv)
        mostrar_valor("Dose que cobre 95% do PTV (cGy)", d95_ptv)
        mostrar_valor("Dose que cobre 98% do PTV (cGy)", d98_ptv)
        mostrar_valor("Dose média na estrutura de isodose de 50% (cGy)", dose_media_iso50)
        mostrar_volume("Volume do PTV", volume_ptv)
        mostrar_volume("Volume da interseção (PTV ∩ 100%)", volume_overlap)
        mostrar_volume("Volume da isodose de 100%", volume_iso100)
        mostrar_volume("Volume da isodose de 50%", volume_iso50)
        
        if tipo_tratamento == "SRS (Radiocirurgia)":
            mostrar_volume("Volume da dose de 10 Gy", volume_10gy)
            mostrar_volume("Volume da dose de 12 Gy", volume_12gy)
            mostrar_volume("Volume da dose de 18 Gy", volume_18gy)
            mostrar_volume("Volume da dose de 20 Gy", volume_20gy)
            mostrar_volume("Volume da dose de 25 Gy", volume_25gy)
            mostrar_volume("Volume da dose de 30 Gy", volume_30gy)

        elif tipo_tratamento == "SBRT de Pulmão":
            volume_pulmao = extrair_volume_por_estrutura(caminho, nome_pulmao)
            mostrar_volume("Volume do Pulmão", volume_pulmao)
            mostrar_volume("Volme do Pulmão recebendo acima de 20Gy", volume_pulmao_20gy)

else:
    st.info("Por favor, selecione o tipo de tratamento na barra lateral. Em seguida, envie um arquivo .txt de DVH tabulado em Upload do Arquivo para iniciar a análise. O DVH tabulado precisa ser de um gráfico cumulativo, com dose absoluta e volume absoluto, contendo, no mínimo, as estruturas de Corpo, PTV, Interseção entre o PTV e a Isodose de Prescrição, e Isodose de 50%. Para o caso de SBRT de Pulmão, também é necessário uma estrutura para o Pulmão a ser avaliado o V20Gy.")






