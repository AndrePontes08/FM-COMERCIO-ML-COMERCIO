import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Relatório Financeiro 2025", layout="wide")

# --- ARQUIVO PADRÃO ---
ARQUIVO_PADRAO = "CONTAS2025-3.csv"

# --- FUNÇÕES DE CATEGORIZAÇÃO ---
def categorizar_imposto(descricao):
    if not isinstance(descricao, str): return None
    d = descricao.upper().strip()
    
    if 'FUNCEP' in d: return "FUNCEP"
    if 'ICMS' in d: return "ICMS"
    if 'IPTU' in d and 'TCR' in d: return "IPTU/TCR"
    if 'IPTU' in d: return "IPTU"
    if 'TCR' in d: return "TCR"
    
    if 'SIMPLES' in d: return "SIMPLES NACIONAL"
    if 'DAS' in d:
        proibidos = ['PLACAS', 'LETRAS', 'FACHADA', 'HOLANDAS', 'DUPLICATA', 'LUZES', 'CORDA', 'MAURICIO']
        if not any(p in d for p in proibidos):
            return "DAS (SIMPLES)"
            
    if 'DARF' in d: return "DARF"
    if 'RECEITA FEDERAL' in d: return "RECEITA FEDERAL"
    if 'IRRF' in d: return "IRRF"
    if 'ISS' in d: return "ISS"
    
    return None

def categorizar_emprestimo(descricao):
    if not isinstance(descricao, str): return None
    d = descricao.upper().strip()
    
    if 'PRONAMPE' in d: return "PRONAMPE"
    
    if 'SICREDI' in d:
        if 'EMPRESTIMO' in d or 'EMPRÉSTIMO' in d or 'PARCELA' in d or '/' in d:
            return "SICREDI"
            
    if 'NORDESTE' in d:
        if 'BANCO' in d:
            return "BANCO DO NORDESTE"
            
    if 'BANCO DO BRASIL' in d: return "BANCO DO BRASIL"
    if ' BB ' in d or d.endswith(' BB') or d.startswith('BB '):
        if 'EMPRESTIMO' in d or 'FINANCIAMENTO' in d:
            return "BANCO DO BRASIL"

    if 'EMPRESTIMO' in d or 'EMPRÉSTIMO' in d or 'FINANCIAMENTO' in d:
        return "OUTROS EMPRÉSTIMOS"
        
    return None

def padronizar_unidade(texto):
    if not isinstance(texto, str): return "OUTROS"
    t = texto.upper().strip()
    if "PES" in t and ("OAL" in t or "0AL" in t): return "PESSOAL"
    if ("FM" in t and "ML" in t): return "FM/ML"
    if t in ["F,", "FB", "FM", "FM.", "FM "]: return "FM"
    if t.startswith("FM"): return "FM"
    if t in ["ML", "ML0", "ML."]: return "ML"
    if t.startswith("ML"): return "ML"
    return "OUTROS"

# --- CARREGAMENTO ---
@st.cache_data
def carregar_dados(caminho_ou_buffer):
    try:
        df = pd.read_csv(caminho_ou_buffer)
        colunas_esperadas = ['data', 'DESCRIÇÃO', 'UNIDADE', 'VALOR']
        if not all(col in df.columns for col in colunas_esperadas):
            if hasattr(caminho_ou_buffer, 'seek'): caminho_ou_buffer.seek(0)
            df = pd.read_csv(caminho_ou_buffer, header=None, skiprows=2)
            df = df.iloc[:, :4]
            df.columns = ['data', 'DESCRIÇÃO', 'UNIDADE', 'VALOR']

        df['data_formatada'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
        
        def limpar_valor(valor):
            if isinstance(valor, str):
                valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
                try: return float(valor)
                except: return 0.0
            elif isinstance(valor, (int, float)): return float(valor)
            return 0.0

        df['valor_numerico'] = df['VALOR'].apply(limpar_valor)
        df['UNIDADE'] = df['UNIDADE'].astype(str).apply(padronizar_unidade)
        
        df['Grupo_Imposto'] = df['DESCRIÇÃO'].apply(categorizar_imposto)
        df['Grupo_Emprestimo'] = df['DESCRIÇÃO'].apply(categorizar_emprestimo)
        
        df_limpo = df.dropna(subset=['data_formatada']).copy()
        df_limpo['Mes_Ano'] = df_limpo['data_formatada'].dt.to_period('M').astype(str)
        
        return df_limpo

    except Exception as e:
        st.error(f"Erro: {e}")
        return None

# --- APP ---
st.sidebar.title("Menu")

if st.sidebar.button("🔄 Recarregar Tabela"):
    st.cache_data.clear()

df = None
if os.path.exists(ARQUIVO_PADRAO):
    df = carregar_dados(ARQUIVO_PADRAO)
else:
    st.sidebar.warning(f"Arquivo {ARQUIVO_PADRAO} não encontrado.")

uploaded = st.sidebar.file_uploader("Carregar CSV", type=['csv'])
if uploaded: df = carregar_dados(uploaded)

if df is not None:
    st.title("📊 Relatório Financeiro 2025")
    
    # --- FILTROS ---
    st.sidebar.header("Filtros")
    
    padrao_inicio = date(2025, 1, 1)
    padrao_fim = date(2025, 12, 31)
    min_arq, max_arq = df['data_formatada'].min().date(), df['data_formatada'].max().date()
    
    d1, d2 = st.sidebar.columns(2)
    inicio = d1.date_input("Início", value=padrao_inicio, min_value=min_arq, max_value=max_arq)
    fim = d2.date_input("Fim", value=padrao_fim, min_value=min_arq, max_value=max_arq)
    
    unis = sorted(df['UNIDADE'].unique())
    sel_unis = st.sidebar.multiselect("Unidades (Visão Geral)", unis, default=unis)
    
    # DataFrame filtrado para Visão Geral (Respeita o filtro de Unidade da sidebar)
    mask_geral = (df['data_formatada'].dt.date >= inicio) & (df['data_formatada'].dt.date <= fim) & (df['UNIDADE'].isin(sel_unis))
    df_f = df[mask_geral]

    # DataFrame filtrado APENAS para PESSOAL (Ignora filtro de Unidade da sidebar, usa apenas Data)
    mask_pessoal = (df['data_formatada'].dt.date >= inicio) & (df['data_formatada'].dt.date <= fim) & (df['UNIDADE'] == 'PESSOAL')
    df_pessoal = df[mask_pessoal]
    
    # --- ABAS ---
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Visão Geral", "🏛️ Impostos", "🏦 Empréstimos", "👤 Gastos Pessoais"])
    
    # ABA 1: GERAL
    with tab1:
        tot = df_f['valor_numerico'].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total Gasto (Seleção)", f"R$ {tot:,.2f}")
        c2.metric("Qtd. Lançamentos", df_f.shape[0])
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        
        evol = df_f.groupby('Mes_Ano')['valor_numerico'].sum().reset_index()
        fig1 = px.bar(evol, x='Mes_Ano', y='valor_numerico', title="Evolução Mensal", text_auto='.2s')
        g1.plotly_chart(fig1, use_container_width=True)
        
        uni = df_f.groupby('UNIDADE')['valor_numerico'].sum().reset_index().sort_values('valor_numerico', ascending=False)
        fig2 = px.bar(uni, x='UNIDADE', y='valor_numerico', color='UNIDADE', title="Por Unidade", text='valor_numerico')
        fig2.update_traces(texttemplate='R$ %{y:,.2f}')
        g2.plotly_chart(fig2, use_container_width=True)

    # ABA 2: IMPOSTOS
    with tab2:
        df_imp = df_f[df_f['Grupo_Imposto'].notnull()]
        if not df_imp.empty:
            tot_imp = df_imp['valor_numerico'].sum()
            st.metric("💰 Total Pago em Impostos", f"R$ {tot_imp:,.2f}")
            c_i1, c_i2 = st.columns(2)
            grp_imp = df_imp.groupby('Grupo_Imposto')['valor_numerico'].sum().reset_index().sort_values('valor_numerico', ascending=True)
            fig_imp = px.bar(grp_imp, y='Grupo_Imposto', x='valor_numerico', orientation='h', title="Ranking: Maiores Impostos", text='valor_numerico')
            fig_imp.update_traces(texttemplate='R$ %{x:,.2f}', textposition='outside')
            c_i1.plotly_chart(fig_imp, use_container_width=True)
            c_i2.dataframe(df_imp[['data', 'DESCRIÇÃO', 'VALOR', 'Grupo_Imposto']], height=400)
        else:
            st.warning("Nenhum imposto encontrado neste período.")

    # ABA 3: EMPRÉSTIMOS
    with tab3:
        df_emp = df_f[df_f['Grupo_Emprestimo'].notnull()]
        if not df_emp.empty:
            tot_emp = df_emp['valor_numerico'].sum()
            st.metric("🏦 Total Pago em Empréstimos", f"R$ {tot_emp:,.2f}")
            c_e1, c_e2 = st.columns(2)
            grp_emp = df_emp.groupby('Grupo_Emprestimo')['valor_numerico'].sum().reset_index().sort_values('valor_numerico', ascending=False)
            fig_emp = px.pie(grp_emp, values='valor_numerico', names='Grupo_Emprestimo', title="Distribuição por Banco", hole=0.4)
            c_e1.plotly_chart(fig_emp, use_container_width=True)
            c_e2.dataframe(df_emp[['data', 'DESCRIÇÃO', 'VALOR', 'Grupo_Emprestimo']], height=400)
        else:
            st.warning("Nenhum empréstimo encontrado neste período.")

    # ABA 4: GASTOS PESSOAIS (NOVA)
    with tab4:
        st.subheader("👤 Análise de Gastos Pessoais")
        
        if not df_pessoal.empty:
            total_pessoal = df_pessoal['valor_numerico'].sum()
            
            # Métricas
            kp1, kp2 = st.columns(2)
            kp1.metric("Total Gasto (Pessoal)", f"R$ {total_pessoal:,.2f}")
            kp2.metric("Lançamentos", df_pessoal.shape[0])
            
            st.markdown("---")
            
            # Filtro de texto para pesquisar dentro dos gastos pessoais
            termo_busca = st.text_input("🔍 Pesquisar despesa específica (Ex: ENERGISA, CARTÃO):")
            if termo_busca:
                df_pessoal_view = df_pessoal[df_pessoal['DESCRIÇÃO'].astype(str).str.contains(termo_busca, case=False, na=False)]
            else:
                df_pessoal_view = df_pessoal

            col_p1, col_p2 = st.columns([2, 1])
            
            with col_p1:
                st.markdown("#### 🏆 Ranking: Maiores Gastos Pessoais")
                # Agrupa por descrição para somar gastos repetidos (Ex: Várias contas de energia)
                ranking_pessoal = df_pessoal_view.groupby('DESCRIÇÃO')['valor_numerico'].sum().reset_index()
                # Pega os Top 15
                ranking_pessoal = ranking_pessoal.sort_values('valor_numerico', ascending=True).tail(15)
                
                fig_rank_pessoal = px.bar(
                    ranking_pessoal, 
                    y='DESCRIÇÃO', 
                    x='valor_numerico', 
                    orientation='h',
                    text='valor_numerico',
                    title="Top 15 Maiores Despesas (Agrupadas)"
                )
                fig_rank_pessoal.update_traces(texttemplate='R$ %{x:,.2f}', textposition='outside')
                fig_rank_pessoal.update_layout(height=600) # Aumenta altura para caber descrições
                st.plotly_chart(fig_rank_pessoal, use_container_width=True)
            
            with col_p2:
                st.markdown("#### 📋 Detalhes")
                st.dataframe(df_pessoal_view[['data', 'DESCRIÇÃO', 'VALOR']].sort_values('data', ascending=False), height=600, use_container_width=True)
                
        else:
            st.warning("Nenhum gasto classificado como 'PESSOAL' encontrado no período selecionado.")

else:
    st.info("Carregando...")
