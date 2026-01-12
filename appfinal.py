import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Relatório Financeiro 2025", layout="wide")

# --- ARQUIVO PADRÃO ---
ARQUIVO_PADRAO = "CONTAS2025-3.csv"

# --- FUNÇÃO DE IDENTIFICAÇÃO DE IMPOSTOS (COM AGRUPAMENTO) ---
def categorizar_imposto(descricao):
    if not isinstance(descricao, str): return None
    d = descricao.upper().strip()
    
    # Regras de Agrupamento (Do mais específico para o mais geral)
    
    # 1. ICMS e FUNCEP
    if 'FUNCEP' in d: return "FUNCEP" # Pega ICMS FUNCEP e joga no grupo FUNCEP
    if 'ICMS' in d: return "ICMS"
    
    # 2. IPTU e TCR
    if 'IPTU' in d and 'TCR' in d: return "IPTU/TCR" # Agrupa quem tem os dois
    if 'IPTU' in d: return "IPTU"
    if 'TCR' in d: return "TCR"
    
    # 3. DAS e SIMPLES (Cuidado com 'DAS PLACAS')
    if 'SIMPLES' in d: return "SIMPLES NACIONAL"
    if 'DAS' in d:
        # Palavras que indicam que NÃO é imposto
        proibidos = ['PLACAS', 'LETRAS', 'FACHADA', 'HOLANDAS', 'DUPLICATA', 'LUZES', 'CORDA', 'MAURICIO']
        if not any(p in d for p in proibidos):
            return "DAS (SIMPLES)"
            
    # 4. Federais
    if 'DARF' in d: return "DARF"
    if 'RECEITA FEDERAL' in d: return "RECEITA FEDERAL"
    if 'IRRF' in d: return "IRRF"
    if 'ISS' in d: return "ISS"
    
    return None

# --- FUNÇÃO DE IDENTIFICAÇÃO DE EMPRÉSTIMOS ---
def categorizar_emprestimo(descricao):
    if not isinstance(descricao, str): return None
    d = descricao.upper().strip()
    
    # Regras de Bancos
    if 'PRONAMPE' in d: return "PRONAMPE"
    
    # Sicredi
    if 'SICREDI' in d:
        if 'EMPRESTIMO' in d or 'EMPRÉSTIMO' in d or 'PARCELA' in d or '/' in d:
            return "SICREDI"
            
    # Banco do Nordeste
    if 'NORDESTE' in d:
        if 'BANCO' in d:
            return "BANCO DO NORDESTE"
            
    # Banco do Brasil
    if 'BANCO DO BRASIL' in d: return "BANCO DO BRASIL"
    if ' BB ' in d or d.endswith(' BB') or d.startswith('BB '):
        if 'EMPRESTIMO' in d or 'FINANCIAMENTO' in d:
            return "BANCO DO BRASIL"

    # Genéricos
    if 'EMPRESTIMO' in d or 'EMPRÉSTIMO' in d or 'FINANCIAMENTO' in d:
        # Se chegou aqui é pq não caiu nos bancos acima, mas é empréstimo
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
        # Leitura flexível
        df = pd.read_csv(caminho_ou_buffer)
        colunas_esperadas = ['data', 'DESCRIÇÃO', 'UNIDADE', 'VALOR']
        if not all(col in df.columns for col in colunas_esperadas):
            if hasattr(caminho_ou_buffer, 'seek'): caminho_ou_buffer.seek(0)
            df = pd.read_csv(caminho_ou_buffer, header=None, skiprows=2)
            df = df.iloc[:, :4]
            df.columns = ['data', 'DESCRIÇÃO', 'UNIDADE', 'VALOR']

        # Conversões
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
        
        # APLICA CATEGORIAS (Cria novas colunas)
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

# Botão Limpar Cache
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
    
    # --- FILTRO DE DATA FIXO EM 2025 ---
    st.sidebar.header("Filtros")
    
    # Definindo padrão para 2025
    padrao_inicio = date(2025, 1, 1)
    padrao_fim = date(2025, 12, 31)
    
    # Garante que as datas padrão estão dentro do limite do arquivo
    min_arq, max_arq = df['data_formatada'].min().date(), df['data_formatada'].max().date()
    
    # Input de data
    d1, d2 = st.sidebar.columns(2)
    inicio = d1.date_input("Início", value=padrao_inicio, min_value=min_arq, max_value=max_arq)
    fim = d2.date_input("Fim", value=padrao_fim, min_value=min_arq, max_value=max_arq)
    
    # Filtro Unidade
    unis = sorted(df['UNIDADE'].unique())
    sel_unis = st.sidebar.multiselect("Unidades", unis, default=unis)
    
    # Filtragem
    mask = (df['data_formatada'].dt.date >= inicio) & (df['data_formatada'].dt.date <= fim) & (df['UNIDADE'].isin(sel_unis))
    df_f = df[mask]
    
    # --- ABAS ---
    tab1, tab2, tab3 = st.tabs(["🏠 Visão Geral", "🏛️ Impostos", "🏦 Empréstimos"])
    
    # ABA 1: GERAL
    with tab1:
        tot = df_f['valor_numerico'].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total Gasto (Período)", f"R$ {tot:,.2f}")
        c2.metric("Qtd. Lançamentos", df_f.shape[0])
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        
        # Evolução
        evol = df_f.groupby('Mes_Ano')['valor_numerico'].sum().reset_index()
        fig1 = px.bar(evol, x='Mes_Ano', y='valor_numerico', title="Evolução Mensal", text_auto='.2s')
        g1.plotly_chart(fig1, use_container_width=True)
        
        # Unidade
        uni = df_f.groupby('UNIDADE')['valor_numerico'].sum().reset_index().sort_values('valor_numerico', ascending=False)
        fig2 = px.bar(uni, x='UNIDADE', y='valor_numerico', color='UNIDADE', title="Por Unidade", text='valor_numerico')
        fig2.update_traces(texttemplate='R$ %{y:,.2f}')
        g2.plotly_chart(fig2, use_container_width=True)

    # ABA 2: IMPOSTOS
    with tab2:
        # Filtra apenas onde achou imposto
        df_imp = df_f[df_f['Grupo_Imposto'].notnull()]
        
        if not df_imp.empty:
            tot_imp = df_imp['valor_numerico'].sum()
            st.metric("💰 Total Pago em Impostos", f"R$ {tot_imp:,.2f}")
            
            c_i1, c_i2 = st.columns(2)
            
            # Gráfico de Ranking Agrupado (Aqui está a mágica: DAS vira uma barra só, ICMS outra, etc)
            grp_imp = df_imp.groupby('Grupo_Imposto')['valor_numerico'].sum().reset_index().sort_values('valor_numerico', ascending=True)
            
            fig_imp = px.bar(grp_imp, y='Grupo_Imposto', x='valor_numerico', orientation='h', 
                             title="Ranking: Maiores Impostos", text='valor_numerico')
            fig_imp.update_traces(texttemplate='R$ %{x:,.2f}', textposition='outside')
            c_i1.plotly_chart(fig_imp, use_container_width=True)
            
            # Tabela
            c_i2.markdown("#### Detalhamento")
            c_i2.dataframe(df_imp[['data', 'DESCRIÇÃO', 'VALOR', 'Grupo_Imposto']], height=400)
        else:
            st.warning("Nenhum imposto encontrado neste período.")

    # ABA 3: EMPRÉSTIMOS
    with tab3:
        # Filtra apenas onde achou empréstimo
        df_emp = df_f[df_f['Grupo_Emprestimo'].notnull()]
        
        if not df_emp.empty:
            tot_emp = df_emp['valor_numerico'].sum()
            st.metric("🏦 Total Pago em Empréstimos", f"R$ {tot_emp:,.2f}")
            
            c_e1, c_e2 = st.columns(2)
            
            # Gráfico de Pizza/Barra Agrupado
            grp_emp = df_emp.groupby('Grupo_Emprestimo')['valor_numerico'].sum().reset_index().sort_values('valor_numerico', ascending=False)
            
            fig_emp = px.pie(grp_emp, values='valor_numerico', names='Grupo_Emprestimo', 
                             title="Distribuição por Banco", hole=0.4)
            c_e1.plotly_chart(fig_emp, use_container_width=True)
            
            # Tabela
            c_e2.markdown("#### Detalhamento")
            c_e2.dataframe(df_emp[['data', 'DESCRIÇÃO', 'VALOR', 'Grupo_Emprestimo']], height=400)
        else:
            st.warning("Nenhum empréstimo encontrado neste período.")

else:
    st.info("Carregando...")