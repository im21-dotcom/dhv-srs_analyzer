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
    return extrair_volume_por_estrutura(filepath, estrutura_alvo="ptv")

def extrair_volume_overlap(filepath):
    return extrair_volume_por_estrutura(filepath, estrutura_alvo="overlap")

def extrair_dose_max_body(filepath):
    return extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo="body", chave="dose máx")

# Novas funções para PTV (mín/máx)
def extrair_dose_max_ptv(filepath):
    return extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo="ptv", chave="dose máx")

def extrair_dose_min_ptv(filepath):
    return extrair_dado_numerico_por_estrutura(filepath, estrutura_alvo="ptv", chave="dose mín")


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
                coletando_dados = (nome_estrutura == estrutura_alvo.lower())
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
    estrutura_alvo = "body"
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
                coletando_dados = (nome_estrutura == "ptv")
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


# bloco de código para o cálculo das métricas IC,IG,IH e Paddick e demais métricas pedidas

def calcular_metricas_avancadas(dose_prescricao, dose_max_body, dose_max_ptv, dose_min_ptv,
                                 volume_ptv, volume_overlap, volume_iso100, volume_iso50,
                                 d2_ptv, d5_ptv, d95_ptv, d98_ptv):
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

st.sidebar.header("Upload do Arquivo")
uploaded_file = st.sidebar.file_uploader("Envie o arquivo .txt do DVH", type="txt")

if uploaded_file is not None:
    # Salvar temporariamente o arquivo para leitura
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        caminho = tmp.name

    # Selecionar número de frações
    n_frações = st.sidebar.selectbox("Selecione o número de frações:", [1, 3, 5])

    # Coletas
    dose_prescricao = extrair_dose_prescricao(caminho)
    dose_max_body = extrair_dose_max_body(caminho)
    dose_max_ptv = extrair_dose_max_ptv(caminho)
    dose_min_ptv = extrair_dose_min_ptv(caminho)
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
        d2_ptv, d5_ptv, d95_ptv, d98_ptv
    )

    # Impressão das métricas
    st.subheader("📈 Métricas Calculadas")
    for nome, valor in metricas.items():
        if valor is not None:
            # Formatação especial para raios
            if 'Raio efetivo' in nome:
                st.write(f"🔹 {nome}: {valor:.3f} cm")
            else:
                try:
                    st.write(f"🔹 {nome}: {valor:.4f}")
                except Exception:
                    st.write(f"🔹 {nome}: {valor}")
        else:
            st.write(f"🔹 {nome}: não calculado (dados insuficientes)")

    # Impressão por fração
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
        mostrar_valor("Dose que cobre 2% do PTV (cGy)", d2_ptv)
        mostrar_valor("Dose que cobre 5% do PTV (cGy)", d5_ptv)
        mostrar_valor("Dose que cobre 95% do PTV (cGy)", d95_ptv)
        mostrar_valor("Dose que cobre 98% do PTV (cGy)", d98_ptv)
        mostrar_volume("Volume do PTV", volume_ptv)
        mostrar_volume("Volume do Overlap (PTV ∩ 100%)", volume_overlap)
        mostrar_volume("Volume da isodose de 100%", volume_iso100)
        mostrar_volume("Volume da isodose de 50%", volume_iso50)
        mostrar_volume("Volume da dose de 10 Gy", volume_10gy)
        mostrar_volume("Volume da dose de 12 Gy", volume_12gy)
        mostrar_volume("Volume da dose de 18 Gy", volume_18gy)
        mostrar_volume("Volume da dose de 20 Gy", volume_20gy)
        mostrar_volume("Volume da dose de 25 Gy", volume_25gy)
        mostrar_volume("Volume da dose de 30 Gy", volume_30gy)

else:
    st.info("Por favor, envie um arquivo .txt de DVH para iniciar a análise.")




