import streamlit as st
import tempfile

# ------------------------- Funções auxiliares -------------------------
#bloco de código para coleta de dados

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

#bloco de código para o cálculo das métricas IC,IG,IH e Paddick

def calcular_metricas_ic_ig_ih_paddick(dose_prescricao, dose_max_body, volume_ptv,
                                       volume_iso100, volume_iso50, volume_overlap):
    metricas = {}

    # Índice de Conformidade (IC)
    if volume_ptv and volume_iso100:
        metricas['Índice de Conformidade (IC)'] = volume_iso100 / volume_ptv
    else:
        metricas['Índice de Conformidade (IC)'] = None

    # Índice de Conformidade de Paddick
    if volume_ptv and volume_iso100 and volume_overlap:
        try:
            metricas['Índice de Conformidade de Paddick (Paddick)'] = (volume_overlap ** 2) / (volume_ptv * volume_iso100)
        except ZeroDivisionError:
            metricas['Índice de Conformidade de Paddick (Paddick)'] = None
    else:
        metricas['Índice de Conformidade de Paddick (Paddick)'] = None

    # Índice de Gradiente (IG)
    if volume_iso100 and volume_iso50:
        metricas['Índice de Gradiente (IG)'] = volume_iso50 / volume_iso100
    else:
        metricas['Índice de Gradiente (IG)'] = None

    # Índice de Homogeneidade (IH)
    if dose_prescricao and dose_max_body:
        metricas['Índice de Homogeneidade (IH)'] = dose_max_body / dose_prescricao
    else:
        metricas['Índice de Homogeneidade (IH)'] = None

    return metricas

def imprimir_metricas(metricas):
    print("\n📈 Métricas Calculadas:")
    for nome, valor in metricas.items():
        if valor is not None:
            print(f"🔹 {nome}: {valor:.4f}")
        else:
            print(f"🔹 {nome}: não calculado (dados insuficientes)")

#bloco de código para coleta de métricas de volumes de dose associadas ao desenvolvimento de radionecrose

def imprimir_metricas_por_fracao(n_frações, volume_10gy=None, volume_12gy=None,
                                  volume_18gy=None, volume_20gy=None,
                                  volume_25gy=None, volume_30gy=None):
    print("\n📦 Volumes de Dose associados ao desenvolvimento de radionecrose:")

    if n_frações == 1:
        print("🔹 Fracionamento: 1 seção de tratamento")
        if volume_10gy is not None:
            print(f"   - Volume de Dose > 10 Gy: {volume_10gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 10 Gy: não encontrado")
        if volume_12gy is not None:
            print(f"   - Volume de Dose > 12 Gy: {volume_12gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 12 Gy: não encontrado")

    elif n_frações == 3:
        print("🔹 Fracionamento: 3 seções de tratamento")
        if volume_18gy is not None:
            print(f"   - Volume de Dose > 18 Gy: {volume_18gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 18 Gy: não encontrado")
        if volume_20gy is not None:
            print(f"   - Volume de Dose > 20 Gy: {volume_20gy:.2f} cm³")
        else:
            print("   - Volume de Dose > 20 Gy: não encontrado")

    elif n_frações == 5:
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

# Supondo que todas as funções estão coladas corretamente aqui...

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

    # Métricas principais
    metricas = calcular_metricas_ic_ig_ih_paddick(
        dose_prescricao, dose_max_body, volume_ptv,
        volume_iso100, volume_iso50, volume_overlap
    )

    # Impressão das métricas
    st.subheader("📈 Métricas Calculadas")
    for nome, valor in metricas.items():
        if valor is not None:
            st.write(f"🔹 {nome}: {valor:.4f}")
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
    if st.checkbox("Deseja ver todos os volumes coletados?"):
        st.subheader("📊 Resumo dos volumes utilizados")

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
        mostrar_valor("Dose máxima na estrutura Body", dose_max_body)
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
