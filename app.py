import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="해외 유망 시장 수출입 분석기",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path):
    """
    CSV 파일을 로드하고 분석 가능한 형태로 전처리하는 함수입니다.
    """
    # 파일 존재 여부 확인 (경로 디버깅용)
    if not os.path.exists(file_path):
        st.error(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        st.info(f"현재 작업 경로: {os.getcwd()}")
        st.info("💡 깃허브에 CSV 파일이 app.py와 같은 폴더에 올라갔는지 확인해주세요.")
        return pd.DataFrame()

    df = pd.DataFrame()
    
    # 1. 인코딩 자동 감지 시도 (cp949 -> utf-8 순서로 시도)
    try:
        df = pd.read_csv(file_path, header=1, encoding='cp949')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_path, header=1, encoding='utf-8')
        except Exception as e:
            st.error(f"파일 인코딩 오류: {e}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"파일 로드 중 알 수 없는 오류 발생: {e}")
        return pd.DataFrame()

    # 2. 컬럼명 공백 제거
    df.columns = df.columns.str.strip()
    
    # 3. 데이터 정제
    try:
        if '순위' not in df.columns:
            st.error("데이터에 '순위' 컬럼이 없습니다. CSV 파일 구조를 확인해주세요.")
            return pd.DataFrame()

        # 순위 데이터 정제
        df['순위_숫자'] = pd.to_numeric(df['순위'], errors='coerce')
        df = df.dropna(subset=['순위_숫자'])
        df['순위'] = df['순위_숫자'].astype(int)
        
        # 숫자형 컬럼 변환
        numeric_cols = [
            '수입액(천$)', '수출액(천$)', '무역수지(천$)',
            '2024 - 수입금액(천$)', '2024 - 수출액(천$)',
            '2023 - 수입금액(천$)', '2023 - 수출액(천$)',
            '2022 - 수입금액(천$)', '2022 - 수출액(천$)'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('-', '0').replace('nan', '0')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0 
                
        return df

    except Exception as e:
        st.error(f"데이터 전처리 오류: {e}")
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# 3. 메인 애플리케이션 로직
# -----------------------------------------------------------------------------
def main():
    st.sidebar.title("🌏 분석 도구 옵션")
    
    # [중요] 깃허브에 올릴 파일명과 100% 일치해야 합니다.
    FILE_PATH = "해외유망시장추천_20260116144351.csv"
    
    df = load_data(FILE_PATH)
    
    if df.empty:
        return

    # 사이드바: 순위 필터
    min_rank, max_rank = int(df['순위'].min()), int(df['순위'].max())
    if max_rank < min_rank: max_rank = min_rank
    
    rank_range = st.sidebar.slider(
        "분석할 국가 순위 범위 (Rank)", 
        min_rank, 
        max_rank, 
        (min_rank, min(max_rank, 20))
    )
    
    filtered_df = df[(df['순위'] >= rank_range[0]) & (df['순위'] <= rank_range[1])]

    st.title("📊 해외 유망 시장 수출입 통계 대시보드")
    st.markdown(f"**분석 범위:** 순위 {rank_range[0]}위 ~ {rank_range[1]}위 국가 (총 {len(filtered_df)}개국)")
    
    # KPI
    col1, col2, col3 = st.columns(3)
    total_import = filtered_df['수입액(천$)'].sum()
    total_export = filtered_df['수출액(천$)'].sum()
    avg_balance = filtered_df['무역수지(천$)'].mean()
    
    col1.metric("선택 국가 총 수입액", f"${total_import:,.0f} (천불)")
    col2.metric("선택 국가 총 수출액", f"${total_export:,.0f} (천불)")
    col3.metric("평균 무역수지", f"${avg_balance:,.0f} (천불)")
    
    st.divider()

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📈 시장 비교", "🌍 상관관계", "🔍 상세 리포트"])
    
    with tab1:
        st.subheader("국가별 수입 및 수출 규모 비교")
        sort_by = st.selectbox("정렬 기준", ['수입액(천$)', '수출액(천$)', '무역수지(천$)'])
        
        fig_bar = px.bar(
            filtered_df.sort_values(sort_by, ascending=False),
            x='수입국',
            y=['수입액(천$)', '수출액(천$)'],
            barmode='group',
            height=500
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.subheader("시장 규모 매트릭스")
        fig_scatter = px.scatter(
            filtered_df,
            x='수입액(천$)',
            y='수출액(천$)',
            size='수입액(천$)', 
            color='수입국',
            hover_name='수입국',
            log_x=True, log_y=True 
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab3:
        st.subheader("국가별 연도별 추이")
        country_list = filtered_df['수입국'].unique()
        
        if len(country_list) > 0:
            selected_country = st.selectbox("국가 선택", country_list)
            
            country_data = df[df['수입국'] == selected_country].iloc[0]
            
            years = ['2022', '2023', '2024']
            try:
                import_vals = [country_data.get(f'{y} - 수입금액(천$)', 0) for y in years]
                export_vals = [country_data.get(f'{y} - 수출액(천$)', 0) for y in years]
                
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=years, y=import_vals, name='수입액', mode='lines+markers'))
                fig_line.add_trace(go.Scatter(x=years, y=export_vals, name='수출액', line=dict(dash='dot'), mode='lines+markers'))
                fig_line.update_layout(title=f"{selected_country} - 3개년 추이", height=400)
                st.plotly_chart(fig_line, use_container_width=True)
            except Exception:
                st.info("연도별 상세 데이터가 부족하여 그래프를 그릴 수 없습니다.")
        else:
            st.info("선택된 범위 내에 국가 데이터가 없습니다.")

    with st.expander("📂 원본 데이터 보기"):
        st.dataframe(filtered_df)

if __name__ == "__main__":
    main()