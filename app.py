import streamlit as st
import google.generativeai as genai
import os
from datetime import datetime
import json

try:
    from knowledge_manager import KnowledgeManager
    from github_manager import GitHubManager
except ImportError as e:
    st.error(f"모듈 로드 실패: {e}")
    st.stop()

# 페이지 설정
st.set_page_config(
    page_title="CT Room Staff Knowledge Assistant",
    page_icon="🏥",
    layout="wide"
)

# API 사용량 추적 파일
USAGE_FILE = "api_usage.json"

def load_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, 'r') as f:
            return json.load(f)
    return {"count": 0, "month": datetime.now().month}

def save_usage(usage_data):
    with open(USAGE_FILE, 'w') as f:
        json.dump(usage_data, f)

def increment_usage():
    usage = load_usage()
    current_month = datetime.now().month
    
    # 월이 바뀌면 카운트 리셋
    if usage["month"] != current_month:
        usage = {"count": 0, "month": current_month}
    
    usage["count"] += 1
    save_usage(usage)
    return usage["count"]

# 환경 감지
is_cloud = os.getenv('STREAMLIT_CLOUD') or 'STREAMLIT_SHARING' in os.environ

# API 키 설정 - 클라우드와 로컬 모두 지원
use_gemini = False
try:
    api_key = st.secrets.get('GOOGLE_API_KEY')
    if api_key and api_key != "your_google_gemini_api_key_here":
        genai.configure(api_key=api_key)
        use_gemini = True
except Exception:
    st.warning("⚠️ API 키 설정이 필요합니다. (선택사항)")

# GitHub 설정 확인
use_github = False
try:
    token = st.secrets.get('GITHUB_TOKEN')
    if token and token != "your_github_token_here":
        use_github = True
except Exception:
    pass

# 지식 관리자 초기화
@st.cache_resource
def init_knowledge_manager():
    return KnowledgeManager()

@st.cache_resource
def init_github_manager():
    if use_github:
        try:
            return GitHubManager(
                st.secrets['GITHUB_TOKEN'],
                st.secrets.get('GITHUB_REPO', 'radpushman/Knowledge_for_CT_Room_Staff')
            )
        except Exception as e:
            st.error(f"GitHub 연동 실패: {e}")
    return None

km = init_knowledge_manager()
gh = init_github_manager()

st.title("🏥 CT Room Staff Knowledge Assistant")

# 시스템 상태 표시
with st.sidebar.expander("📊 시스템 정보"):
    if km:
        stats = km.get_stats()
        st.write(f"📚 총 지식: {stats['total_documents']}개")
        st.write(f"🗂️ 카테고리별:")
        for category, count in stats['categories'].items():
            st.write(f"  - {category}: {count}개")
        st.write(f"🔄 마지막 업데이트: {stats['last_updated'][:16] if stats['last_updated'] != 'N/A' else 'N/A'}")

# 배포 정보 표시
if is_cloud:
    st.success("🌐 웹에서 실행 중 - 어디서든 접근 가능!")
    st.info("💡 팀원들과 이 링크를 공유하여 함께 사용하세요!")
else:
    st.info("💻 로컬 환경에서 실행 중")

# 초기 지식 데이터 로드 (웹 배포시 기본 데이터 제공)
if is_cloud and not os.path.exists("./knowledge"):
    with st.expander("📚 기본 지식 데이터 로드"):
        if st.button("기본 CT 지식 데이터 로드"):
            success = load_default_knowledge(km)
            if success:
                st.success("기본 지식이 로드되었습니다!")
                st.rerun()

# 사이드바 - 기능 선택과 사용량 표시
st.sidebar.title("기능 선택")

# 웹 배포 안내
if is_cloud:
    with st.sidebar.expander("🌐 웹 배포 정보"):
        st.markdown("""
        ✅ **현재 웹에서 실행 중**
        - 어디서든 접근 가능
        - 팀원들과 공유 가능
        - 자동 백업 (GitHub 연동시)
        """)
else:
    with st.sidebar.expander("🚀 웹 배포 하기"):
        st.markdown("""
        **Streamlit Cloud 배포 단계:**
        1. GitHub에 코드 업로드
        2. share.streamlit.io 접속
        3. 저장소 선택 후 배포
        4. 시크릿 설정 완료
        
        ✨ **웹 배포 장점:**
        - 어디서든 접근
        - 팀 협업 가능
        - 자동 업데이트
        """)

if use_gemini:
    usage = load_usage()
    st.sidebar.info(f"이번 달 AI 사용량: {usage['count']}/15")
    if usage['count'] >= 15:
        st.sidebar.warning("무료 한도 초과! 검색 모드만 사용 가능합니다.")

# GitHub 상태 표시
if use_github:
    st.sidebar.success("✅ GitHub 연동됨")
    if st.sidebar.button("🔄 GitHub에서 동기화"):
        with st.spinner("GitHub에서 최신 지식을 가져오는 중..."):
            success = gh.sync_from_github()
            if success:
                st.sidebar.success("동기화 완료!")
                st.rerun()
            else:
                st.sidebar.error("동기화 실패")
else:
    st.sidebar.warning("GitHub 미연동 (로컬만 사용)")

mode = st.sidebar.selectbox(
    "모드를 선택하세요:",
    ["💬 질문하기", "📝 지식 추가", "📚 지식 검색", "✏️ 지식 편집", "🔄 GitHub 관리"]
)

if mode == "💬 질문하기":
    st.header("자연어로 질문하기")
    
    # Gemini API 역할 설명
    st.info("""
    🤖 **Gemini 1.5 API의 역할:**
    - 검색된 지식을 바탕으로 자연어 답변 생성
    - 복합적인 질문에 대한 통합적 답변 제공
    - CT실 직원이 이해하기 쉽게 답변 재구성
    """)
    
    user_question = st.text_input("궁금한 것을 자연어로 입력하세요:")
    
    if user_question:
        # 1단계: 관련 지식 검색 (ChromaDB/키워드 검색)
        with st.spinner("관련 지식을 검색하는 중..."):
            relevant_docs = km.search_knowledge(user_question)
        
        # 2단계: Gemini API를 통한 답변 생성 (선택사항)
        if use_gemini and load_usage()["count"] < 15:
            with st.spinner("🤖 AI가 검색된 자료를 분석하여 답변을 생성중입니다..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                context = "\n\n".join([doc['content'] for doc in relevant_docs])
                
                # Gemini에게 주는 명확한 역할 정의
                prompt = f"""
                당신은 CT실 전문 지식 어시스턴트입니다.
                
                다음 참고자료를 바탕으로 질문에 답변해주세요:
                
                참고자료:
                {context}
                
                질문: {user_question}
                
                답변 규칙:
                1. 한국어로 답변
                2. CT실 직원이 이해하기 쉽게 설명
                3. 참고자료에 없는 내용은 추측하지 말고 "참고자료에 없음"이라고 명시
                4. 중요한 안전사항이 있으면 강조
                5. 단계별로 설명이 필요한 경우 번호를 매겨서 설명
                """
                
                try:
                    response = model.generate_content(prompt)
                    increment_usage()
                    
                    st.markdown("### 🤖 AI 종합 답변")
                    st.success("✨ Gemini AI가 검색된 자료를 분석하여 답변을 재구성했습니다.")
                    st.markdown(response.text)
                    
                    # AI 답변의 한계 명시
                    with st.expander("ℹ️ AI 답변에 대한 주의사항"):
                        st.warning("""
                        **중요:** 
                        - AI 답변은 등록된 지식 자료를 바탕으로 생성됩니다
                        - 의료적 판단이 필요한 경우 반드시 의료진과 상담하세요
                        - 응급상황에서는 기존 프로토콜을 우선 적용하세요
                        """)
                        
                except Exception as e:
                    st.error(f"AI 답변 생성 실패: {e}")
                    st.info("AI 답변 생성에 실패했지만, 아래 검색된 자료를 확인하세요.")
        else:
            # Gemini API 없이도 작동하는 기본 검색
            st.markdown("### 📚 검색된 관련 자료")
            if not relevant_docs:
                st.info("관련 자료를 찾을 수 없습니다. 새로운 지식을 추가해보세요.")
            else:
                st.success(f"💡 {len(relevant_docs)}개의 관련 자료를 찾았습니다. 직접 확인해보세요.")
                
            # API 없을 때 안내
            if not use_gemini:
                with st.expander("🤖 AI 답변 기능 활성화하기"):
                    st.info("""
                    **Gemini AI 답변 기능을 사용하려면:**
                    1. Google AI Studio에서 무료 API 키 발급
                    2. Streamlit Secrets에 API 키 추가
                    3. 월 15회 무료로 AI 답변 이용 가능
                    
                    **AI 없이도 가능한 기능:**
                    - 키워드 검색으로 관련 자료 찾기
                    - 카테고리별 지식 검색
                    - 지식 추가/편집/삭제
                    """)
            
        # 3단계: 원본 검색 결과 표시 (항상 표시)
        if relevant_docs:
            st.markdown("### 📋 검색된 원본 자료")
            for i, doc in enumerate(relevant_docs[:3]):
                with st.expander(f"📄 {doc['title']} - {doc['category']}"):
                    st.markdown(doc['content'])
                    if doc.get('tags'):
                        st.markdown(f"**태그:** {doc['tags']}")
                    
                    # 편집 버튼 추가
                    if st.button("✏️ 이 자료 편집", key=f"edit_from_qa_{i}"):
                        st.session_state.edit_knowledge = doc
                        st.session_state.edit_mode = True
                        st.rerun()

elif mode == "📝 지식 추가":
    st.header("새로운 지식 추가")
    
    title = st.text_input("제목:")
    category = st.selectbox("카테고리:", 
                           ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"])
    content = st.text_area("내용:", height=300)
    tags = st.text_input("태그 (쉼표로 구분):")
    
    # GitHub 백업 옵션
    backup_to_github = False
    if use_github:
        backup_to_github = st.checkbox("GitHub에 자동 백업", value=True)
    
    if st.button("지식 추가"):
        if title and content:
            success = km.add_knowledge(title, content, category, tags)
            if success:
                st.success("지식이 성공적으로 추가되었습니다!")
                
                # GitHub 백업
                if backup_to_github and gh:
                    with st.spinner("GitHub에 백업 중..."):
                        backup_success = gh.backup_knowledge(title, content, category, tags)
                        if backup_success:
                            st.success("GitHub 백업 완료!")
                        else:
                            st.warning("GitHub 백업 실패 (로컬에는 저장됨)")
                
                st.rerun()
            else:
                st.error("지식 추가에 실패했습니다.")
        else:
            st.error("제목과 내용을 모두 입력해주세요.")

elif mode == "📚 지식 검색":
    st.header("지식 검색")
    
    search_query = st.text_input("검색어를 입력하세요:")
    
    if search_query:
        results = km.search_knowledge(search_query)
        
        st.markdown(f"### 검색 결과 ({len(results)}개)")
        
        for i, result in enumerate(results):
            with st.expander(f"📄 {result['title']} - {result['category']}"):
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(result['content'])
                    if result.get('tags'):
                        st.markdown(f"**태그:** {result['tags']}")
                
                with col2:
                    if st.button("✏️ 편집", key=f"edit_{i}"):
                        st.session_state.edit_knowledge = result
                        st.session_state.edit_mode = True
                        st.rerun()

elif mode == "✏️ 지식 편집":
    st.header("지식 편집")
    
    # 편집할 지식이 선택되지 않은 경우
    if 'edit_knowledge' not in st.session_state:
        st.info("편집할 지식을 선택하세요.")
        
        # 모든 지식 목록 표시
        all_knowledge = km.get_all_knowledge()
        
        if all_knowledge:
            st.subheader("📚 모든 지식 목록")
            
            for i, knowledge in enumerate(all_knowledge):
                with st.expander(f"📄 {knowledge['title']} - {knowledge['category']}"):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(knowledge['content'][:200] + "..." if len(knowledge['content']) > 200 else knowledge['content'])
                        if knowledge.get('tags'):
                            st.markdown(f"**태그:** {knowledge['tags']}")
                    
                    with col2:
                        if st.button("✏️ 편집", key=f"edit_all_{i}"):
                            st.session_state.edit_knowledge = knowledge
                            st.session_state.edit_mode = True
                            st.rerun()
                        
                        if st.button("🗑️ 삭제", key=f"delete_{i}"):
                            if st.session_state.get(f"confirm_delete_{i}", False):
                                success = km.delete_knowledge(knowledge['id'])
                                if success:
                                    st.success("지식이 삭제되었습니다!")
                                    if 'edit_knowledge' in st.session_state:
                                        del st.session_state.edit_knowledge
                                    st.rerun()
                                else:
                                    st.error("삭제에 실패했습니다.")
                            else:
                                st.session_state[f"confirm_delete_{i}"] = True
                                st.warning("한 번 더 클릭하면 삭제됩니다.")
                                st.rerun()
        else:
            st.info("등록된 지식이 없습니다. 먼저 지식을 추가해주세요.")
    
    # 편집 모드
    else:
        knowledge = st.session_state.edit_knowledge
        
        st.success(f"📝 편집 중: {knowledge['title']}")
        
        # 편집 폼
        new_title = st.text_input("제목:", value=knowledge['title'])
        new_category = st.selectbox("카테고리:", 
                                   ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"],
                                   index=["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"].index(knowledge['category']) if knowledge['category'] in ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"] else 4)
        new_content = st.text_area("내용:", value=knowledge['content'], height=300)
        new_tags = st.text_input("태그 (쉼표로 구분):", value=knowledge.get('tags', ''))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 저장"):
                if new_title and new_content:
                    success = km.update_knowledge(
                        knowledge['id'], 
                        new_title, 
                        new_content, 
                        new_category, 
                        new_tags
                    )
                    if success:
                        st.success("지식이 성공적으로 수정되었습니다!")
                        
                        # GitHub 백업
                        if use_github and gh:
                            backup_success = gh.backup_knowledge(new_title, new_content, new_category, new_tags)
                            if backup_success:
                                st.success("GitHub 백업 완료!")
                            else:
                                st.warning("GitHub 백업 실패 (로컬에는 저장됨)")
                        
                        del st.session_state.edit_knowledge
                        st.rerun()
                    else:
                        st.error("수정에 실패했습니다.")
                else:
                    st.error("제목과 내용을 모두 입력해주세요.")
        
        with col2:
            if st.button("❌ 취소"):
                del st.session_state.edit_knowledge
                if 'edit_mode' in st.session_state:
                    del st.session_state.edit_mode
                st.rerun()
        
        with col3:
            if st.button("🗑️ 삭제"):
                if st.session_state.get("confirm_delete_edit", False):
                    success = km.delete_knowledge(knowledge['id'])
                    if success:
                        st.success("지식이 삭제되었습니다!")
                        del st.session_state.edit_knowledge
                        if 'edit_mode' in st.session_state:
                            del st.session_state.edit_mode
                        st.rerun()
                    else:
                        st.error("삭제에 실패했습니다.")
                else:
                    st.session_state.confirm_delete_edit = True
                    st.warning("한 번 더 클릭하면 삭제됩니다.")
                    st.rerun()

elif mode == "🔄 GitHub 관리":
    st.header("GitHub 저장소 관리")
    
    if not use_github:
        st.warning("GitHub 연동이 설정되지 않았습니다.")
        st.markdown("""
        GitHub 연동을 위해 다음을 설정하세요:
        1. GitHub Personal Access Token 생성
        2. `.streamlit/secrets.toml`에 토큰 추가
        3. 저장소 이름 설정
        """)
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 백업")
            if st.button("모든 지식 GitHub에 백업"):
                with st.spinner("전체 백업 중..."):
                    success = gh.backup_all_knowledge(km)
                    if success:
                        st.success("전체 백업 완료!")
                    else:
                        st.error("백업 실패")
        
        with col2:
            st.subheader("📥 복원")
            if st.button("GitHub에서 모든 지식 가져오기"):
                with st.spinner("복원 중..."):
                    success = gh.restore_all_knowledge(km)
                    if success:
                        st.success("복원 완료!")
                        st.rerun()
                    else:
                        st.error("복원 실패")
        
        st.subheader("📊 저장소 정보")
        if gh:
            repo_info = gh.get_repo_info()
            if repo_info:
                st.json(repo_info)

# 기본 지식 로드 함수 추가
def load_default_knowledge(km):
    """웹 배포시 기본 CT 지식 로드"""
    try:
        default_knowledge = [
            {
                "title": "CT 스캔 기본 프로토콜",
                "category": "프로토콜",
                "content": "CT 스캔의 기본적인 촬영 순서와 환자 준비사항입니다.\n\n1. 환자 확인 및 동의서 작성\n2. 금속 제거 확인\n3. 조영제 주입 여부 확인\n4. 환자 위치 설정\n5. 스캔 범위 설정\n6. 촬영 실시",
                "tags": "기본, 프로토콜, 촬영"
            },
            {
                "title": "조영제 부작용 대응",
                "category": "응급상황",
                "content": "조영제 투여 후 발생할 수 있는 부작용과 대응방법입니다.\n\n**경미한 반응:**\n- 구역, 구토\n- 두드러기\n- 가려움\n\n**중증 반응:**\n- 호흡곤란\n- 혈압 저하\n- 의식 저하\n\n즉시 의료진 호출 및 응급처치 실시",
                "tags": "조영제, 응급, 부작용"
            },
            {
                "title": "CT 장비 일일 점검사항",
                "category": "장비운용",
                "content": "매일 실시해야 할 CT 장비 점검 항목입니다.\n\n1. 갠트리 작동 확인\n2. 테이블 이동 확인\n3. 냉각 시스템 점검\n4. 조영제 주입기 점검\n5. 응급장비 확인\n6. 점검 기록 작성",
                "tags": "장비, 점검, 일일"
            }
        ]
        
        for knowledge in default_knowledge:
            km.add_knowledge(
                knowledge["title"],
                knowledge["content"],
                knowledge["category"],
                knowledge["tags"]
            )
        return True
    except Exception as e:
        st.error(f"기본 지식 로드 실패: {e}")
        return False
