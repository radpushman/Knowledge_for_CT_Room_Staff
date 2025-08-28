import streamlit as st
import json
import base64
import requests
from datetime import datetime
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(page_title="CT위키", page_icon="🏥", layout="wide")
st.title("🏥 CT위키")

# 보안 코드 (환경 변수로 변경 가능)
SECURITY_CODE = st.secrets.get("SECURITY_CODE", "2398")

# LocalStorage JavaScript 코드
localStorage_js = """
<script>
function saveToLocalStorage(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
}

function loadFromLocalStorage(key) {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
}

window.addEventListener('message', function(event) {
    if (event.data.type === 'GET_STORAGE') {
        const data = loadFromLocalStorage('ct_knowledge_db');
        window.parent.postMessage({type: 'STORAGE_DATA', data: data}, '*');
    } else if (event.data.type === 'SET_STORAGE') {
        saveToLocalStorage('ct_knowledge_db', event.data.data);
        window.parent.postMessage({type: 'STORAGE_SAVED'}, '*');
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const data = loadFromLocalStorage('ct_knowledge_db');
    window.parent.postMessage({type: 'STORAGE_DATA', data: data}, '*');
});
</script>
"""

# JavaScript 컴포넌트 렌더링
components.html(localStorage_js, height=0)

# 세션 상태 초기화
if 'knowledge_db' not in st.session_state:
    st.session_state.knowledge_db = {
        "documents": {},
        "last_updated": datetime.now().isoformat()
    }

# 기본 지식 로드 (최초 1회만)
if 'initialized' not in st.session_state:
    default_docs = [
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
        }
    ]
    
    # 기존 데이터가 없으면 기본 지식만 로드
    if len(st.session_state.knowledge_db["documents"]) == 0:
        for i, doc in enumerate(default_docs):
            doc_id = f"default_{i+1}"
            st.session_state.knowledge_db["documents"][doc_id] = {
                "id": doc_id,
                "title": doc["title"],
                "content": doc["content"],
                "category": doc["category"],
                "tags": doc["tags"],
                "created_at": datetime.now().isoformat()
            }
    
    st.session_state.initialized = True

# LocalStorage 데이터 로드
js_load_code = """
<script>
window.parent.postMessage({type: 'GET_STORAGE'}, '*');
</script>
"""
components.html(js_load_code, height=0)

# 데이터 저장 함수
def save_knowledge_db():
    """지식 DB를 LocalStorage에 저장"""
    try:
        js_code = f"""
        <script>
        localStorage.setItem('ct_knowledge_db', JSON.stringify({json.dumps(st.session_state.knowledge_db)}));
        console.log('Data saved to localStorage');
        </script>
        """
        components.html(js_code, height=0)
        st.session_state.knowledge_db["last_updated"] = datetime.now().isoformat()
    except Exception as e:
        st.error(f"저장 오류: {e}")

# 지식 관리 함수들
def add_knowledge(title, content, category, tags):
    doc_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{abs(hash(title)) % 10000}"
    st.session_state.knowledge_db["documents"][doc_id] = {
        "id": doc_id,
        "title": title,
        "content": content,
        "category": category,
        "tags": tags,
        "created_at": datetime.now().isoformat()
    }
    save_knowledge_db()
    return True

def search_knowledge(query):
    results = []
    query_lower = query.lower()
    
    for doc in st.session_state.knowledge_db["documents"].values():
        score = 0
        if query_lower in doc["title"].lower():
            score += 20
        if query_lower in doc["content"].lower():
            score += 10
        if query_lower in doc["category"].lower():
            score += 15
        if query_lower in doc["tags"].lower():
            score += 15
        
        if score > 0:
            doc_copy = doc.copy()
            doc_copy["score"] = score
            results.append(doc_copy)
    
    return sorted(results, key=lambda x: x["score"], reverse=True)[:5]

def get_all_knowledge():
    docs = list(st.session_state.knowledge_db["documents"].values())
    return sorted(docs, key=lambda x: x["created_at"], reverse=True)

def update_knowledge(doc_id, title, content, category, tags):
    if doc_id in st.session_state.knowledge_db["documents"]:
        old_created = st.session_state.knowledge_db["documents"][doc_id]["created_at"]
        st.session_state.knowledge_db["documents"][doc_id] = {
            "id": doc_id,
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "created_at": old_created,
            "updated_at": datetime.now().isoformat()
        }
        save_knowledge_db()
        return True
    return False

def delete_knowledge(doc_id):
    if doc_id in st.session_state.knowledge_db["documents"]:
        del st.session_state.knowledge_db["documents"][doc_id]
        save_knowledge_db()
        return True
    return False

# 백업 함수
def backup_to_github():
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets.get("GITHUB_REPO", "radpushman/Knowledge_for_CT_Room_Staff")
        backup_data = {
            "backup_time": datetime.now().isoformat(),
            "total_documents": len(st.session_state.knowledge_db["documents"]),
            "knowledge_db": st.session_state.knowledge_db
        }
        content = json.dumps(backup_data, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        url = f"https://api.github.com/repos/{repo}/contents/ct_knowledge_backup.json"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        response = requests.get(url, headers=headers, timeout=30)
        sha = response.json().get("sha") if response.status_code == 200 else None
        data = {
            "message": f"Backup CT knowledge - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({len(st.session_state.knowledge_db['documents'])}개 문서)",
            "content": content_b64,
            "committer": {
                "name": "CT Wiki Bot",
                "email": "bot@example.com",
                "date": datetime.now().isoformat()
            }
        }
        if sha:
            data["sha"] = sha
        backup_response = requests.put(url, headers=headers, json=data, timeout=30)
        if backup_response.status_code in [200, 201]:
            return f"백업 성공! ({len(st.session_state.knowledge_db['documents'])}개 문서)"
        return f"백업 실패: {backup_response.status_code} - {backup_response.json().get('message', backup_response.text[:200])}"
    except Exception as e:
        return f"백업 오류: {str(e)}"

# 복원 함수
def restore_from_github(security_code):
    if security_code != SECURITY_CODE:
        return "❌ 잘못된 보안 코드입니다."
    
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets.get("GITHUB_REPO", "radpushman/Knowledge_for_CT_Room_Staff")
        
        url = f"https://api.github.com/repos/{repo}/contents/ct_knowledge_backup.json"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 404:
            return "❌ GitHub에 백업 파일이 없습니다."
        elif response.status_code != 200:
            return f"❌ GitHub 접근 실패: {response.status_code}"
        
        file_info = response.json()
        download_url = file_info.get("download_url")
        
        if not download_url:
            return "❌ 백업 파일 다운로드 URL을 찾을 수 없습니다."
        
        content_response = requests.get(download_url, timeout=30)
        if content_response.status_code != 200:
            return f"❌ 백업 파일 다운로드 실패: {content_response.status_code}"
        
        backup_data = json.loads(content_response.text)
        restored_db = backup_data.get("knowledge_db", {})
        
        if not restored_db or "documents" not in restored_db:
            return "❌ 유효하지 않은 백업 데이터입니다."
        
        st.session_state.knowledge_db = restored_db
        save_knowledge_db()
        
        doc_count = len(restored_db.get("documents", {}))
        backup_time = backup_data.get("backup_time", "알 수 없음")
        
        return f"✅ 복원 성공! {doc_count}개 문서 복원 (백업일시: {backup_time[:16]})"
        
    except Exception as e:
        return f"❌ 복원 처리 오류: {str(e)}"

# 사이드바 정보
total_docs = len(st.session_state.knowledge_db["documents"])
st.sidebar.info(f"📚 총 지식: {total_docs}개")

# GitHub 백업/복원
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ GitHub 백업/복원")

if st.sidebar.button("💾 GitHub에 백업", type="primary"):
    with st.sidebar:
        with st.spinner("백업 중..."):
            result = backup_to_github()
            if "성공" in result:
                st.success(result)
            else:
                st.error(result)

st.sidebar.markdown("**📥 복원 (보안 코드 필요)**")
restore_code = st.sidebar.text_input(
    "복원 보안 코드:", 
    type="password", 
    key="restore_security",
    help="관리자에게 문의하세요"
)

if st.sidebar.button("📥 GitHub에서 복원"):
    if restore_code:
        with st.sidebar:
            with st.spinner("복원 중..."):
                result = restore_from_github(restore_code)
                if "성공" in result:
                    st.success(result)
                    st.rerun()
                else:
                    st.error(result)
    else:
        st.sidebar.error("보안 코드를 입력하세요.")

# 메인 기능 선택
st.sidebar.markdown("---")
mode = st.sidebar.radio(
    "🔧 기능 선택",
    ["💬 질문하기", "📝 지식 추가", "📚 지식 검색", "✏️ 지식 편집"]
)

# 질문하기
if mode == "💬 질문하기":
    st.header("💬 말하듯 질문해요")
    
    question = st.text_input("궁금한 것을 입력하세요:", placeholder="예: 조영제 부작용")
    
    if question:
        results = search_knowledge(question)
        
        if results:
            st.success(f"🎯 {len(results)}개의 관련 자료를 찾았습니다!")
            
            for doc in results:
                with st.expander(f"📄 {doc['title']} - {doc['category']}"):
                    st.markdown(doc['content'])
                    if doc.get('tags'):
                        st.caption(f"태그: {doc['tags']}")
        else:
            st.warning("관련 자료를 찾을 수 없습니다.")

# 지식 추가
elif mode == "📝 지식 추가":
    st.header("📝 새로운 지식 추가")
    
    security_input = st.text_input(
        "보안 코드:", 
        type="password",
        key="security_add",
        help="승인받은 직원에게 문의하세요"
    )
    
    if security_input == SECURITY_CODE:
        st.success("✅ 승인됨")
        
        with st.form("add_knowledge_form"):
            title = st.text_input("제목:")
            category = st.selectbox("카테고리:", 
                                   ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"])
            content = st.text_area("내용:", height=250)
            tags = st.text_input("태그 (쉼표로 구분):")
            
            submitted = st.form_submit_button("➕ 지식 추가")
            
            if submitted:
                if title and content:
                    add_knowledge(title, content, category, tags)
                    st.success("✅ 지식이 추가되었습니다!")
                    st.balloons()
                    st.info("💡 중요한 지식은 정기적으로 GitHub에 백업하세요!")
                else:
                    st.error("제목과 내용을 입력해주세요.")
    
    elif security_input:
        st.error("❌ 잘못된 보안 코드")
    else:
        st.info("💡 지식을 추가하려면 보안 코드를 입력하세요.")

# 지식 검색
elif mode == "📚 지식 검색":
    st.header("📚 지식 검색")
    
    search_term = st.text_input("검색어:", placeholder="예: 프로토콜, 조영제, 장비")
    
    if search_term:
        results = search_knowledge(search_term)
        
        if results:
            st.success(f"🔍 검색 결과: {len(results)}개")
            
            for doc in results:
                with st.expander(f"📄 {doc['title']} - {doc['category']} (관련도: {doc['score']})"):
                    st.markdown(doc['content'])
                    if doc.get('tags'):
                        st.caption(f"태그: {doc['tags']}")
        else:
            st.warning("검색 결과가 없습니다.")
            
            all_docs = get_all_knowledge()
            if all_docs:
                st.info("📚 등록된 모든 지식:")
                for doc in all_docs[:3]:
                    st.write(f"• {doc['title']} ({doc['category']})")

# 지식 편집
elif mode == "✏️ 지식 편집":
    st.header("✏️ 지식 편집")
    
    all_docs = get_all_knowledge()
    
    if all_docs:
        doc_titles = [f"{doc['title']} ({doc['category']})" for doc in all_docs]
        selected_idx = st.selectbox("편집할 지식 선택:", range(len(doc_titles)), 
                                   format_func=lambda x: doc_titles[x])
        
        selected_doc = all_docs[selected_idx]
        
        st.info(f"선택됨: {selected_doc['title']}")
        
        security_edit = st.text_input(
            "편집 보안 코드:", 
            type="password",
            key="security_edit"
        )
        
        if security_edit == SECURITY_CODE:
            st.success("✅ 편집 권한 확인")
            
            with st.form("edit_knowledge_form"):
                new_title = st.text_input("제목:", value=selected_doc['title'])
                new_category = st.selectbox("카테고리:", 
                                           ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"],
                                           index=["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"].index(selected_doc['category']) if selected_doc['category'] in ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"] else 4)
                new_content = st.text_area("내용:", value=selected_doc['content'], height=250)
                new_tags = st.text_input("태그:", value=selected_doc.get('tags', ''))
                
                col1, col2 = st.columns(2)
                with col1:
                    update_btn = st.form_submit_button("💾 수정 저장")
                with col2:
                    delete_btn = st.form_submit_button("🗑️ 삭제", type="secondary")
                
                if update_btn:
                    if new_title and new_content:
                        update_knowledge(selected_doc['id'], new_title, new_content, new_category, new_tags)
                        st.success("✅ 수정 완료!")
                        st.rerun()
                    else:
                        st.error("제목과 내용을 입력해주세요.")
                
                if delete_btn:
                    delete_knowledge(selected_doc['id'])
                    st.success("🗑️ 삭제 완료!")
                    st.rerun()
        
        elif security_edit:
            st.error("❌ 잘못된 보안 코드")
    else:
        st.info("편집할 지식이 없습니다.")

# 하단 정보
st.markdown("---")
st.markdown("### 💾 데이터 보존 시스템")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **🔒 로컬 저장**
    - 브라우저 LocalStorage에 영구 저장
    - 리부트해도 데이터 유지
    - 팀원별 개별 저장
    """)

with col2:
    st.markdown("""
    **☁️ 클라우드 백업**
    - GitHub에 수동 백업 가능
    - 전체 팀원과 공유
    - 보안 코드로 복원 보호
    """)

st.caption("💡 중요한 지식은 정기적으로 GitHub 백업을 권장합니다.")
