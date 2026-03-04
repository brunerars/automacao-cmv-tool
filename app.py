"""
Sistema de Análise de CMV - ARV Industrial
Aplicação Principal Streamlit
"""

import streamlit as st
import pandas as pd
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Análise de CMV - ARV",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .os-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
    }
    .os-title {
        font-size: 20px;
        font-weight: bold;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 10px;
    }
    .badge-estourado { background-color: #e74c3c; color: white; }
    .badge-critico { background-color: #e67e22; color: white; }
    .badge-atencao { background-color: #f1c40f; color: black; }
    .badge-ok { background-color: #27ae60; color: white; }
    .badge-cinza { background-color: #95a5a6; color: white; }

    .metric-row {
        display: flex;
        gap: 30px;
        margin: 10px 0;
        flex-wrap: wrap;
    }
    .metric-item {
        text-align: center;
    }
    .metric-label {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
    }
    .metric-value {
        font-size: 18px;
        font-weight: bold;
    }
    .metric-value-red { color: #e74c3c; }
    .metric-value-green { color: #27ae60; }

    .exec-bar-container {
        background-color: rgba(255,255,255,0.1);
        border-radius: 5px;
        height: 12px;
        margin: 10px 0;
        overflow: hidden;
    }
    .exec-bar {
        height: 100%;
        border-radius: 5px;
        transition: width 0.3s ease;
    }

    .familia-row {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        border-left: 4px solid;
    }
    .familia-estourado { background-color: rgba(231, 76, 60, 0.15); border-left-color: #e74c3c; }
    .familia-critico { background-color: rgba(230, 126, 34, 0.15); border-left-color: #e67e22; }
    .familia-atencao { background-color: rgba(241, 196, 15, 0.15); border-left-color: #f1c40f; }
    .familia-ok { background-color: rgba(39, 174, 96, 0.15); border-left-color: #27ae60; }
    .familia-cinza { background-color: rgba(149, 165, 166, 0.15); border-left-color: #95a5a6; }

    .familia-name {
        flex: 2;
        font-weight: 500;
    }
    .familia-values {
        flex: 3;
        display: flex;
        gap: 15px;
        font-size: 13px;
    }
    .familia-exec {
        flex: 1;
        text-align: right;
        font-weight: bold;
    }

    .summary-card {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# FUNÇÕES DE PROCESSAMENTO
# =====================================================

def detectar_formato(df_raw):
    """Detecta o formato da planilha: 'raw_erp' ou 'comprador'"""
    first_row = [str(c).strip().upper() for c in df_raw.iloc[0].tolist()]
    if 'EMPRESA' in first_row or 'NUMERO_SERVICO' in first_row:
        return 'raw_erp'
    return 'comprador'


def processar_raw_erp(df_raw):
    """Parser para o formato RAW-ERP (6 colunas com EMPRESA e NUMERO_SERVICO)"""
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.iloc[0]]
    df = df.iloc[1:].reset_index(drop=True)

    df = df.rename(columns={
        'NUMERO_SERVICO': 'OS',
        'VALORTOTALCOMPRADO': 'REALIZADO'
    })

    df = df[['OS', 'FAMILIA', 'PREVISTO', 'REALIZADO', 'SALDO']].copy()

    df = df[df['OS'].notna()].copy()

    for col in ['PREVISTO', 'REALIZADO', 'SALDO']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['OS'] = df['OS'].astype(str).str.strip()
    df['FAMILIA'] = df['FAMILIA'].astype(str).str.strip()

    return df


def processar_planilha(uploaded_file):
    """Pipeline de processamento da planilha"""
    df_raw = pd.read_excel(uploaded_file, header=None)

    formato = detectar_formato(df_raw)

    if formato == 'raw_erp':
        st.info("ℹ️ Formato detectado: **RAW-ERP** (exportação direta do sistema)")
        return processar_raw_erp(df_raw)

    st.info("ℹ️ Formato detectado: **Planilha Formatada** (layout padrão comprador)")

    header_row = None
    for idx in range(min(10, len(df_raw))):
        first_cell = str(df_raw.iloc[idx, 0]).strip().upper()
        if first_cell in ['O_S', 'OS', 'O.S.', 'O.S']:
            header_row = idx
            break

    if header_row is None:
        st.error("❌ Não foi possível identificar o cabeçalho.")
        return None

    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = ['OS', 'FAMILIA', 'PREVISTO', 'REALIZADO', 'SALDO']
    df = df.reset_index(drop=True)

    df = df[df['OS'].notna()].copy()
    df = df[~df['OS'].astype(str).str.upper().isin(['O_S', 'OS', 'O.S.', 'O.S'])].copy()

    for col in ['PREVISTO', 'REALIZADO', 'SALDO']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['OS'] = df['OS'].astype(str).str.strip()
    df['FAMILIA'] = df['FAMILIA'].astype(str).str.strip()

    return df

def agregar_por_os(df):
    """Agrega dados por OS"""
    return df.groupby('OS').agg({
        'PREVISTO': 'sum',
        'REALIZADO': 'sum',
        'SALDO': 'sum'
    }).reset_index()

def classificar_risco(previsto, realizado):
    """Classifica o risco baseado na execução"""
    if previsto == 0:
        if realizado > 0:
            return 'CRÍTICO'
        return 'SEM ORÇAMENTO'

    exec_pct = (realizado / previsto) * 100

    if exec_pct > 100:
        return 'ESTOURADO'
    elif exec_pct >= 90:
        return 'CRÍTICO'
    elif exec_pct >= 70:
        return 'ATENÇÃO'
    else:
        return 'OK'

def get_cor_risco(risco):
    """Retorna cor baseada no risco"""
    cores = {
        'OK': '#27ae60',
        'ATENÇÃO': '#f1c40f',
        'CRÍTICO': '#e67e22',
        'ESTOURADO': '#e74c3c',
        'SEM ORÇAMENTO': '#95a5a6'
    }
    return cores.get(risco, '#95a5a6')

def get_classe_risco(risco):
    """Retorna classe CSS baseada no risco"""
    classes = {
        'OK': 'ok',
        'ATENÇÃO': 'atencao',
        'CRÍTICO': 'critico',
        'ESTOURADO': 'estourado',
        'SEM ORÇAMENTO': 'cinza'
    }
    return classes.get(risco, 'cinza')

def formatar_moeda(valor):
    """Formata valor para padrão brasileiro"""
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_moeda_compacto(valor):
    """Formata valor de forma compacta"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0"
    if abs(valor) >= 1_000_000:
        milhoes = f"{valor/1_000_000:.1f}".replace(".", ",")
        return f"R$ {milhoes}M"
    if abs(valor) >= 1_000:
        return f"R$ {valor/1_000:.0f}K"
    return f"R$ {valor:.0f}"

def criar_excel_download(df):
    """Cria arquivo Excel para download"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()

def render_os_card(os_num, df_os_row, df_familias):
    """Renderiza um card de OS com expander para famílias"""

    previsto = df_os_row['PREVISTO']
    realizado = df_os_row['REALIZADO']
    saldo = df_os_row['SALDO']
    exec_pct = (realizado / previsto * 100) if previsto > 0 else 0
    risco = classificar_risco(previsto, realizado)
    cor = get_cor_risco(risco)
    classe = get_classe_risco(risco)

    # Contagem de famílias por status
    fam_status = {}
    for _, fam in df_familias.iterrows():
        fam_risco = classificar_risco(fam['PREVISTO'], fam['REALIZADO'])
        fam_status[fam_risco] = fam_status.get(fam_risco, 0) + 1

    # Emoji indicador
    emoji_risco = {'ESTOURADO': '🔴', 'CRÍTICO': '🟠', 'ATENÇÃO': '🟡', 'OK': '🟢'}.get(risco, '⚪')

    # Título do expander com informações resumidas (curto e sem markdown)
    # Mantém o "Previsto → Realizado" no header sem poluir a UI.
    previsto_label = formatar_moeda_compacto(previsto).replace("R$", r"R\$")
    realizado_label = formatar_moeda_compacto(realizado).replace("R$", r"R\$")
    saldo_label = formatar_moeda_compacto(saldo).replace("R$", r"R\$")
    titulo = (
        f"{emoji_risco} OS {os_num} • {risco} • "
        f"{previsto_label} → {realizado_label} • Saldo: {saldo_label} • {exec_pct:.0f}%"
    )

    with st.expander(titulo, expanded=False):
        # Header com métricas principais
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-item">
                <div class="metric-label">Previsto</div>
                <div class="metric-value">{formatar_moeda(previsto)}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Realizado</div>
                <div class="metric-value">{formatar_moeda(realizado)}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Saldo</div>
                <div class="metric-value {'metric-value-red' if saldo < 0 else 'metric-value-green'}">{formatar_moeda(saldo)}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Execução</div>
                <div class="metric-value">{exec_pct:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Barra de execução
        bar_width = min(exec_pct, 100)
        st.markdown(f"""
        <div class="exec-bar-container">
            <div class="exec-bar" style="width: {bar_width}%; background-color: {cor};"></div>
        </div>
        """, unsafe_allow_html=True)

        # Resumo de status das famílias
        st.markdown("#### 📦 Breakdown por Família")

        status_text = []
        if fam_status.get('ESTOURADO', 0) > 0:
            status_text.append(f"🔴 {fam_status['ESTOURADO']} estouradas")
        if fam_status.get('CRÍTICO', 0) > 0:
            status_text.append(f"🟠 {fam_status['CRÍTICO']} críticas")
        if fam_status.get('ATENÇÃO', 0) > 0:
            status_text.append(f"🟡 {fam_status['ATENÇÃO']} atenção")
        if fam_status.get('OK', 0) > 0:
            status_text.append(f"🟢 {fam_status['OK']} ok")

        if status_text:
            st.caption(" | ".join(status_text))

        # Lista de famílias
        df_familias_sorted = df_familias.copy()
        df_familias_sorted['EXEC_%'] = (df_familias_sorted['REALIZADO'] / df_familias_sorted['PREVISTO'].replace(0, float('nan')) * 100).fillna(0)
        df_familias_sorted = df_familias_sorted.sort_values('EXEC_%', ascending=False)

        for _, fam in df_familias_sorted.iterrows():
            fam_nome = fam['FAMILIA']
            fam_prev = fam['PREVISTO']
            fam_real = fam['REALIZADO']
            fam_saldo = fam['SALDO']
            fam_exec = fam['EXEC_%']
            fam_risco = classificar_risco(fam_prev, fam_real)
            fam_classe = get_classe_risco(fam_risco)
            fam_cor = get_cor_risco(fam_risco)

            saldo_class = 'metric-value-red' if fam_saldo < 0 else 'metric-value-green'

            st.markdown(f"""
            <div class="familia-row familia-{fam_classe}">
                <div class="familia-name">{fam_nome}</div>
                <div class="familia-values">
                    <span>Prev: {formatar_moeda(fam_prev)}</span>
                    <span>Real: {formatar_moeda(fam_real)}</span>
                    <span class="{saldo_class}">Saldo: {formatar_moeda(fam_saldo)}</span>
                </div>
                <div class="familia-exec" style="color: {fam_cor}">{fam_exec:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

# =====================================================
# INTERFACE PRINCIPAL
# =====================================================

st.title("📊 Análise de CMV - ARV Industrial")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    uploaded_file = st.file_uploader(
        "Carregar Planilha CMV",
        type=["xlsx", "xls"],
        help="Aceita dois formatos: Planilha Formatada (O_S | FAMILIA | PREVISTO | REALIZADO | SALDO) ou RAW-ERP (EMPRESA | NUMERO_SERVICO | FAMILIA | PREVISTO | VALORTOTALCOMPRADO | SALDO)"
    )
    st.markdown("---")

if uploaded_file is not None:
    with st.spinner("Processando..."):
        df = processar_planilha(uploaded_file)

    if df is not None:
        # Filtros na sidebar
        with st.sidebar:
            st.header("🔍 Filtros")

            def limpar_filtros():
                st.session_state["filtro_status"] = []
                st.session_state["os_selecionadas"] = []
                st.session_state["familias_selecionadas"] = []
                st.session_state["busca_os"] = ""

            st.button("Limpar filtros", on_click=limpar_filtros, use_container_width=True)

            filtro_status = st.multiselect(
                "Status",
                options=['ESTOURADO', 'CRÍTICO', 'ATENÇÃO', 'OK', 'SEM ORÇAMENTO'],
                key="filtro_status",
                help="Filtrar por classificação de risco"
            )

            os_list = sorted(df['OS'].unique().tolist())
            busca_os = st.text_input(
                "Buscar OS",
                key="busca_os",
                placeholder="Ex: 3185",
                help="Filtra as opções de OS pelo texto digitado"
            )
            if busca_os:
                busca = busca_os.strip().lower()
                os_list_filtrada = [os for os in os_list if busca in str(os).lower()]
            else:
                os_list_filtrada = os_list
            os_list_filtrada = sorted(set(os_list_filtrada + st.session_state.get("os_selecionadas", [])))
            os_selecionadas = st.multiselect("Ordem de Serviço", options=os_list_filtrada, key="os_selecionadas")

            familias_list = sorted(df['FAMILIA'].unique().tolist())
            familias_selecionadas = st.multiselect("Família", options=familias_list, key="familias_selecionadas")

        # Aplicar filtros
        df_filtrado = df.copy()
        if os_selecionadas:
            df_filtrado = df_filtrado[df_filtrado['OS'].isin(os_selecionadas)]
        if familias_selecionadas:
            df_filtrado = df_filtrado[df_filtrado['FAMILIA'].isin(familias_selecionadas)]

        if len(df_filtrado) == 0:
            st.warning(
                "Nenhum dado encontrado com os filtros atuais. "
                "Dica: limpe os filtros ou remova algum critério para voltar a ver resultados."
            )
            st.stop()

        # Agregar por OS
        df_os = agregar_por_os(df_filtrado)
        df_os['EXECUCAO_%'] = (df_os['REALIZADO'] / df_os['PREVISTO'].replace(0, float('nan')) * 100).fillna(0)
        df_os['RISCO'] = df_os.apply(lambda row: classificar_risco(row['PREVISTO'], row['REALIZADO']), axis=1)

        # Aplicar filtro de status
        if filtro_status:
            df_os = df_os[df_os['RISCO'].isin(filtro_status)]

        # Ordenar por execução
        df_os = df_os.sort_values('EXECUCAO_%', ascending=False)

        # Contadores totais
        df_os_total = agregar_por_os(df)
        df_os_total['RISCO'] = df_os_total.apply(lambda row: classificar_risco(row['PREVISTO'], row['REALIZADO']), axis=1)

        n_estourado = len(df_os_total[df_os_total['RISCO'] == 'ESTOURADO'])
        n_critico = len(df_os_total[df_os_total['RISCO'] == 'CRÍTICO'])
        n_atencao = len(df_os_total[df_os_total['RISCO'] == 'ATENÇÃO'])
        n_ok = len(df_os_total[df_os_total['RISCO'] == 'OK'])
        n_sem_orcamento = len(df_os_total[df_os_total['RISCO'] == 'SEM ORÇAMENTO'])

        # ===== RESUMO =====
        st.markdown("---")

        # Métricas
        total_previsto = df_os['PREVISTO'].sum()
        total_realizado = df_os['REALIZADO'].sum()
        total_saldo = df_os['SALDO'].sum()
        exec_geral = (total_realizado / total_previsto * 100) if total_previsto > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Previsto", formatar_moeda_compacto(total_previsto))
        with col2:
            st.metric("💸 Realizado", formatar_moeda_compacto(total_realizado))
        with col3:
            st.metric("📊 Saldo", formatar_moeda_compacto(total_saldo),
                     delta="Negativo!" if total_saldo < 0 else None,
                     delta_color="inverse" if total_saldo < 0 else "normal")
        with col4:
            st.metric("📈 Execução", f"{exec_geral:.1f}%")

        # Status cards
        st.markdown("### 🚦 Resumo por Status")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="summary-card" style="background: linear-gradient(135deg, #e74c3c, #c0392b);">
                <h1 style="color: white; margin: 0; font-size: 36px;">{n_estourado}</h1>
                <p style="color: white; margin: 5px 0 0 0; font-weight: bold;">ESTOURADAS</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="summary-card" style="background: linear-gradient(135deg, #e67e22, #d35400);">
                <h1 style="color: white; margin: 0; font-size: 36px;">{n_critico}</h1>
                <p style="color: white; margin: 5px 0 0 0; font-weight: bold;">CRÍTICAS</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="summary-card" style="background: linear-gradient(135deg, #f1c40f, #f39c12);">
                <h1 style="color: #333; margin: 0; font-size: 36px;">{n_atencao}</h1>
                <p style="color: #333; margin: 5px 0 0 0; font-weight: bold;">ATENÇÃO</p>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="summary-card" style="background: linear-gradient(135deg, #27ae60, #1e8449);">
                <h1 style="color: white; margin: 0; font-size: 36px;">{n_ok}</h1>
                <p style="color: white; margin: 5px 0 0 0; font-weight: bold;">OK</p>
            </div>
            """, unsafe_allow_html=True)

        if n_sem_orcamento > 0:
            st.caption(f"⚪ Sem orçamento: {n_sem_orcamento}")

        st.markdown("---")

        # ===== ABAS =====
        tab1, tab2, tab3 = st.tabs(["🎯 OSs por Execução", "📦 Visão por Família", "📋 Exportar"])

        # ===== ABA 1: OSs =====
        with tab1:
            st.markdown(f"### 📋 Lista de OSs ({len(df_os)} projetos)")
            st.caption("Clique em uma OS para ver o breakdown por família. Ordenado por % de execução.")

            if len(df_os) == 0:
                detalhes = []
                if filtro_status:
                    detalhes.append(f"Status: {', '.join(filtro_status)}")
                if os_selecionadas:
                    detalhes.append(f"OS: {', '.join(map(str, os_selecionadas[:10]))}{'…' if len(os_selecionadas) > 10 else ''}")
                if familias_selecionadas:
                    detalhes.append(f"Família: {', '.join(map(str, familias_selecionadas[:5]))}{'…' if len(familias_selecionadas) > 5 else ''}")

                msg = "Nenhuma OS encontrada com os filtros selecionados."
                if detalhes:
                    msg += " (" + " | ".join(detalhes) + ")"
                msg += " Dica: tente limpar filtros ou remover algum critério."
                st.warning(msg)
            else:
                # Renderizar cards expansíveis
                for _, os_row in df_os.iterrows():
                    os_num = os_row['OS']
                    # Pegar dados das famílias desta OS
                    df_familias_os = df_filtrado[df_filtrado['OS'] == os_num].copy()
                    render_os_card(os_num, os_row, df_familias_os)

        # ===== ABA 2: FAMÍLIAS =====
        with tab2:
            st.markdown("### 📦 Visão Consolidada por Família")

            # Agregar por família (total)
            df_familia = df_filtrado.groupby('FAMILIA').agg({
                'PREVISTO': 'sum',
                'REALIZADO': 'sum',
                'SALDO': 'sum'
            }).reset_index()

            df_familia['EXEC_%'] = (df_familia['REALIZADO'] / df_familia['PREVISTO'].replace(0, float('nan')) * 100).fillna(0)
            df_familia['RISCO'] = df_familia.apply(lambda row: classificar_risco(row['PREVISTO'], row['REALIZADO']), axis=1)
            df_familia = df_familia.sort_values('EXEC_%', ascending=False)

            # Mostrar famílias como cards também
            for _, fam in df_familia.iterrows():
                fam_nome = fam['FAMILIA']
                fam_prev = fam['PREVISTO']
                fam_real = fam['REALIZADO']
                fam_saldo = fam['SALDO']
                fam_exec = fam['EXEC_%']
                fam_risco = fam['RISCO']
                fam_classe = get_classe_risco(fam_risco)
                fam_cor = get_cor_risco(fam_risco)

                emoji = {'ESTOURADO': '🔴', 'CRÍTICO': '🟠', 'ATENÇÃO': '🟡', 'OK': '🟢'}.get(fam_risco, '⚪')

                # Quantas OSs usam essa família
                oss_familia = df_filtrado[df_filtrado['FAMILIA'] == fam_nome]['OS'].nunique()

                with st.expander(f"{emoji} **{fam_nome}** | {fam_risco} | Exec: {fam_exec:.0f}% | {oss_familia} OSs"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Previsto", formatar_moeda(fam_prev))
                    with col2:
                        st.metric("Realizado", formatar_moeda(fam_real))
                    with col3:
                        delta_color = "inverse" if fam_saldo < 0 else "normal"
                        st.metric("Saldo", formatar_moeda(fam_saldo),
                                 delta="Negativo" if fam_saldo < 0 else "Positivo",
                                 delta_color=delta_color)
                    with col4:
                        st.metric("Execução", f"{fam_exec:.1f}%")

                    # Mostrar quais OSs usam essa família
                    st.markdown("##### OSs que usam esta família:")
                    df_oss_fam = df_filtrado[df_filtrado['FAMILIA'] == fam_nome].copy()
                    df_oss_fam['EXEC_%'] = (df_oss_fam['REALIZADO'] / df_oss_fam['PREVISTO'].replace(0, float('nan')) * 100).fillna(0)
                    df_oss_fam = df_oss_fam.sort_values('EXEC_%', ascending=False)

                    for _, row in df_oss_fam.iterrows():
                        os_risco = classificar_risco(row['PREVISTO'], row['REALIZADO'])
                        os_classe = get_classe_risco(os_risco)
                        os_cor = get_cor_risco(os_risco)
                        os_exec = row['EXEC_%']
                        saldo_class = 'metric-value-red' if row['SALDO'] < 0 else 'metric-value-green'

                        st.markdown(f"""
                        <div class="familia-row familia-{os_classe}">
                            <div class="familia-name">OS {row['OS']}</div>
                            <div class="familia-values">
                                <span>Prev: {formatar_moeda(row['PREVISTO'])}</span>
                                <span>Real: {formatar_moeda(row['REALIZADO'])}</span>
                                <span class="{saldo_class}">Saldo: {formatar_moeda(row['SALDO'])}</span>
                            </div>
                            <div class="familia-exec" style="color: {os_cor}">{os_exec:.0f}%</div>
                        </div>
                        """, unsafe_allow_html=True)

        # ===== ABA 3: EXPORTAR =====
        with tab3:
            st.markdown("### 📥 Exportar Dados")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Dados Detalhados (OS + Família)")
                csv1 = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "📥 Baixar CSV Detalhado",
                    data=csv1,
                    file_name="cmv_detalhado.csv",
                    mime="text/csv"
                )

            with col2:
                st.markdown("#### Resumo por OS")
                df_export_os = df_os[['OS', 'PREVISTO', 'REALIZADO', 'SALDO', 'EXECUCAO_%', 'RISCO']].copy()
                csv2 = df_export_os.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "📥 Baixar CSV por OS",
                    data=csv2,
                    file_name="cmv_por_os.csv",
                    mime="text/csv"
                )

            st.markdown("---")
            st.markdown("#### 📋 Preview dos Dados")
            st.dataframe(df_filtrado.head(100), use_container_width=True, height=400, hide_index=True)

else:
    st.info("👆 Faça upload da planilha CMV para começar")

    st.markdown("""
    ### Como usar:
    1. Exporte a planilha de CMV do sistema
    2. Faça upload usando o menu lateral
    3. **Clique em uma OS** para expandir e ver o breakdown por família
    4. Cada família tem sua própria cor de status

    ### Classificação de Risco (por % de execução):
    - 🔴 **ESTOURADO**: > 100%
    - 🟠 **CRÍTICO**: ≥ 90%
    - 🟡 **ATENÇÃO**: 70% - 90%
    - 🟢 **OK**: < 70%
    """)

    st.markdown("---")
    st.caption("Desenvolvido por Bruno | ARV Industrial | 2026")
