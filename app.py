import streamlit as st
import json
import base64
import requests
import os
import time
from datetime import datetime, timedelta

# Gemini API 추가
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# 페이지 설정
st.set_page_config(page_title="CT위키", page_icon="🏥", layout="wide")
st.title("🏥 CT위키")

# 보안 코드 - Secrets에서 가져오거나 기본값 사용 (노출 안됨)
SECURITY_CODE = st.secrets.get("SECURITY_CODE", "2398")

# Gemini API 설정
use_gemini = False
if GEMINI_AVAILABLE:
    try:
        api_key = st.secrets.get('GOOGLE_API_KEY')
        if api_key and api_key != "your_google_gemini_api_key_here":
            genai.configure(api_key=api_key)
            use_gemini = True
    except Exception:
        pass

# API 사용량 추적
USAGE_FILE = "api_usage.json"

def load_usage():
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"count": 0, "date": datetime.now().date().isoformat()}

def save_usage(usage_data):
    try:
        with open(USAGE_FILE, 'w') as f:
            json.dump(usage_data, f)
    except:
        pass

def increment_usage():
    usage = load_usage()
    current_date = datetime.now().date().isoformat()
    
    if usage["date"] != current_date:
        usage = {"count": 0, "date": current_date}
    
    usage["count"] += 1
    save_usage(usage)
    return usage["count"]

# 자동 백업 설정
AUTO_BACKUP_INTERVAL = 30  # 30분 간격
AUTO_BACKUP_KEY = "last_auto_backup"

def should_auto_backup():
    """자동 백업이 필요한지 확인"""
    try:
        if AUTO_BACKUP_KEY not in st.session_state:
            st.session_state[AUTO_BACKUP_KEY] = datetime.now()
            return True
        
        last_backup = st.session_state[AUTO_BACKUP_KEY]
        now = datetime.now()
        
        # 30분이 지났는지 확인
        if (now - last_backup).total_seconds() > AUTO_BACKUP_INTERVAL * 60:
            return True
        
        return False
    except:
        return False

def perform_auto_backup():
    """자동 백업 실행"""
    try:
        # GitHub 토큰이 있는 경우에만 실행
        token = st.secrets.get("GITHUB_TOKEN")
        if not token:
            return False
        
        # 데이터 변경이 있는 경우에만 백업
        current_docs = len(st.session_state.knowledge_db["documents"])
        if current_docs == 0:
            return False
        
        # 백업 실행
        result = backup_to_github()
        
        if "성공" in result:
            st.session_state[AUTO_BACKUP_KEY] = datetime.now()
            # 조용한 알림 (너무 방해하지 않게)
            with st.sidebar:
                st.success("🔄 자동 백업 완료", icon="✅")
            return True
        else:
            # 실패 시에도 시간 업데이트 (무한 재시도 방지)
            st.session_state[AUTO_BACKUP_KEY] = datetime.now()
            return False
            
    except Exception as e:
        st.session_state[AUTO_BACKUP_KEY] = datetime.now()
        return False

# 세션 상태 초기화
if 'knowledge_db' not in st.session_state:
    st.session_state.knowledge_db = {
        "documents": {},
        "last_updated": datetime.now().isoformat()
    }

# 앱 시작 시 GitHub 자동 복원 (간단 버전)
if 'restored' not in st.session_state:
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        if token:
            url = f"https://api.github.com/repos/radpushman/Knowledge_for_CT_Room_Staff/contents/ct_knowledge_backup.json"
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                file_info = response.json()
                content_response = requests.get(file_info["download_url"], timeout=5)
                if content_response.status_code == 200:
                    backup_data = json.loads(content_response.text)
                    if "knowledge_db" in backup_data:
                        st.session_state.knowledge_db = backup_data["knowledge_db"]
                        st.success(f"✅ GitHub에서 {len(backup_data['knowledge_db']['documents'])}개 지식 복원!")
    except:
        pass  # 복원 실패해도 무시
    
    # 복원 실패하거나 지식이 없으면 기본 지식 로드
    if len(st.session_state.knowledge_db["documents"]) == 0:
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
    
    st.session_state.restored = True

# 자동 백업 체크 (앱 로드 시)
if 'auto_backup_checked' not in st.session_state:
    if should_auto_backup():
        perform_auto_backup()
    st.session_state.auto_backup_checked = True

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
    
    # 즉시 백업 옵션 (중요한 변경사항)
    token = st.secrets.get("GITHUB_TOKEN")
    if token and len(st.session_state.knowledge_db["documents"]) <= 5:  # 문서가 적으면 즉시 백업
        try:
            backup_to_github()
            st.session_state[AUTO_BACKUP_KEY] = datetime.now()
        except:
            pass
    
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
        return True
    return False

def delete_knowledge(doc_id):
    if doc_id in st.session_state.knowledge_db["documents"]:
        del st.session_state.knowledge_db["documents"][doc_id]
        return True
    return False

# 간단한 GitHub 백업
def backup_to_github():
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        if not token:
            return "❌ GitHub 토큰이 설정되지 않았습니다"
        
        backup_data = {
            "backup_time": datetime.now().isoformat(),
            "total_documents": len(st.session_state.knowledge_db["documents"]),
            "knowledge_db": st.session_state.knowledge_db
        }
        
        content = json.dumps(backup_data, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        url = f"https://api.github.com/repos/radpushman/Knowledge_for_CT_Room_Staff/contents/ct_knowledge_backup.json"
        headers = {"Authorization": f"Bearer {token}"}
        
        # 기존 파일 확인
        response = requests.get(url, headers=headers, timeout=10)
        data = {
            "message": f"Backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64
        }
        
        if response.status_code == 200:
            data["sha"] = response.json()["sha"]
        
        backup_response = requests.put(url, headers=headers, json=data, timeout=10)
        
        if backup_response.status_code in [200, 201]:
            return f"✅ 백업 성공! ({len(st.session_state.knowledge_db['documents'])}개 문서)"
        else:
            return f"❌ 백업 실패: {backup_response.status_code}"
    except Exception as e:
        return f"❌ 백업 오류: {str(e)}"

# 간단한 복원
def restore_from_github(security_code):
    if security_code != SECURITY_CODE:
        return "❌ 잘못된 보안 코드입니다"
    
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        if not token:
            return "❌ GitHub 토큰이 설정되지 않았습니다"
        
        url = f"https://api.github.com/repos/radpushman/Knowledge_for_CT_Room_Staff/contents/ct_knowledge_backup.json"
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"❌ 백업 파일 없음: {response.status_code}"
        
        file_info = response.json()
        content_response = requests.get(file_info["download_url"], timeout=10)
        
        if content_response.status_code == 200:
            backup_data = json.loads(content_response.text)
            if "knowledge_db" in backup_data:
                st.session_state.knowledge_db = backup_data["knowledge_db"]
                doc_count = len(backup_data["knowledge_db"]["documents"])
                return f"✅ 복원 성공! {doc_count}개 문서"
            else:
                return "❌ 잘못된 백업 데이터"
        else:
            return f"❌ 다운로드 실패: {content_response.status_code}"
    except Exception as e:
        return f"❌ 복원 오류: {str(e)}"

# 백업 시간 확인 함수 추가
def get_backup_info():
    """GitHub 백업 파일의 최종 백업 시간 확인"""
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        if not token:
            return None
        
        url = f"https://api.github.com/repos/radpushman/Knowledge_for_CT_Room_Staff/contents/ct_knowledge_backup.json"
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            file_info = response.json()
            # GitHub API에서 파일 수정 시간 가져오기
            content_response = requests.get(file_info["download_url"], timeout=10)
            if content_response.status_code == 200:
                backup_data = json.loads(content_response.text)
                backup_time = backup_data.get("backup_time")
                total_docs = backup_data.get("total_documents", 0)
                
                if backup_time:
                    # ISO 시간을 서울 시간으로 변환
                    from datetime import datetime, timezone, timedelta
                    
                    # UTC 시간을 datetime 객체로 변환
                    backup_dt = datetime.fromisoformat(backup_time.replace('Z', '+00:00'))
                    
                    # 서울 시간대 (UTC+9) 적용
                    seoul_tz = timezone(timedelta(hours=9))
                    seoul_time = backup_dt.astimezone(seoul_tz)
                    
                    # 서울 시간으로 포맷팅
                    formatted_time = seoul_time.strftime('%m월 %d일 %H:%M')
                    
                    return {
                        "backup_time": formatted_time,
                        "total_docs": total_docs,
                        "raw_time": backup_time
                    }
        return None
    except Exception as e:
        return None

# 사이드바
total_docs = len(st.session_state.knowledge_db["documents"])
st.sidebar.info(f"📚 총 지식: {total_docs}개")

# GitHub 백업/복원
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ GitHub 관리")

# 백업 정보 표시 (자동 백업 상태 추가)
backup_info = get_backup_info()
if backup_info:
    # 다음 자동 백업 시간 계산
    next_backup = st.session_state.get(AUTO_BACKUP_KEY, datetime.now()) + timedelta(minutes=AUTO_BACKUP_INTERVAL)
    time_until_backup = next_backup - datetime.now()
    
    if time_until_backup.total_seconds() > 0:
        minutes_left = int(time_until_backup.total_seconds() / 60)
        backup_status = f"🔄 {minutes_left}분 후 자동백업"
    else:
        backup_status = "🔄 자동백업 대기중"
    
    st.sidebar.info(f"""
📅 **최종 백업**
{backup_info['backup_time']} (서울시간)
📄 {backup_info['total_docs']}개 문서
{backup_status}
""")
else:
    st.sidebar.warning("📅 백업 정보 없음")

if st.sidebar.button("💾 백업"):
    result = backup_to_github()
    if "성공" in result:
        st.sidebar.success(result)
        st.rerun()  # 백업 후 정보 새로고침
    else:
        st.sidebar.error(result)

restore_code = st.sidebar.text_input("복원 코드:", type="password", key="restore")

if st.sidebar.button("📥 복원"):
    if restore_code:
        # 복원 전에 백업 정보 확인하여 사용자에게 알림
        if backup_info:
            st.sidebar.info(f"📥 {backup_info['backup_time']} 백업을 복원합니다...")
        
        result = restore_from_github(restore_code)
        if "성공" in result:
            st.sidebar.success(result)
            st.rerun()
        else:
            st.sidebar.error(result)
    else:
        st.sidebar.error("복원 코드를 입력하세요")

# 자동 백업 설정 (사이드바에 추가)
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ 백업 설정")

# 자동 백업 상태 표시
if st.secrets.get("GITHUB_TOKEN"):
    st.sidebar.success("🔄 자동 백업 활성화 (30분 간격)")
    
    # 수동으로 자동 백업 트리거
    if st.sidebar.button("🔄 지금 자동백업 실행"):
        with st.sidebar:
            with st.spinner("백업 중..."):
                if perform_auto_backup():
                    st.success("백업 완료!")
                    st.rerun()
                else:
                    st.error("백업 실패")
else:
    st.sidebar.warning("🔄 자동 백업 비활성화 (토큰 없음)")

# 사이드바에 AI 사용량 표시
if use_gemini:
    usage = load_usage()
    st.sidebar.info(f"🤖 오늘 AI 사용량: {usage['count']}/1,500")
    if usage['count'] >= 1500:
        st.sidebar.warning("일일 무료 한도 초과!")
else:
    # Gemini API 상태 디버깅 정보 추가
    st.sidebar.warning("🤖 AI 기능 비활성화됨")
    
    # 디버깅 정보 표시
    with st.sidebar.expander("🔧 AI 상태 확인"):
        st.write(f"GEMINI_AVAILABLE: {GEMINI_AVAILABLE}")
        
        api_key = st.secrets.get('GOOGLE_API_KEY')
        if api_key:
            if api_key == "your_google_gemini_api_key_here":
                st.write("❌ API 키가 기본값입니다")
            else:
                st.write(f"✅ API 키 설정됨: {api_key[:10]}...")
        else:
            st.write("❌ API 키가 설정되지 않음")
        
        st.write(f"use_gemini: {use_gemini}")

# 메인 기능
st.sidebar.markdown("---")
mode = st.sidebar.radio("기능 선택", ["💬 질문하기", "📝 지식 추가", "📚 지식 검색", "✏️ 지식 편집"])

if mode == "💬 질문하기":
    st.header("💬 질문하기")
    
    # Gemini API 상태 표시
    if use_gemini:
        st.success("🤖 Gemini 1.5 Flash AI 답변 활성화됨")
    else:
        st.warning("🤖 현재 키워드 검색만 가능 (AI 답변 비활성화)")
    
    question = st.text_input("궁금한 것을 입력하세요:", placeholder="예: 조영제 부작용 대응 방법")
    
    if question:
        # 1단계: 관련 지식 검색
        with st.spinner("관련 지식을 검색하는 중..."):
            results = search_knowledge(question)
        
        if results:
            st.success(f"🎯 {len(results)}개의 관련 자료를 찾았습니다!")
            
            # 2단계: Gemini AI 답변 생성 (활성화된 경우에만)
            if use_gemini and load_usage()["count"] < 1500:
                st.info("🤖 AI가 답변을 생성합니다...")
                with st.spinner("🤖 AI가 검색된 자료를 분석하여 답변을 생성 중..."):
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        # 검색된 지식을 컨텍스트로 제공
                        context = "\n\n".join([f"**{doc['title']}**\n{doc['content']}" for doc in results])
                        
                        prompt = f"""
당신은 CT실 동료입니다. 간결하되 도움이 되게 답변하세요.

검색된 자료:
{context}

질문: {question}

답변 규칙:
1. 검색된 자료 내용을 충실히 반영
2. 핵심 내용만 간결하게 설명 (3-5문장 정도)
3. 검색된 자료에 없으면 "자료에 없음"이라고 명시
4. 중요한 안전사항이나 절차가 있으면 간단히 언급
5. 필요시 번호로 정리

예시 길이:
- "조영제 부작용" → 경미한 반응과 중증 반응을 간단히 구분해서 2-3줄로 설명
- "마코 환자번호" → 시스템 용도와 입력 방법을 간단히 1-2줄로 설명
"""

                        response = model.generate_content(prompt)
                        increment_usage()
                        
                        st.markdown("### 🤖 AI 종합 답변")
                        st.success("✨ Gemini 1.5 Flash가 검색된 자료를 분석하여 답변을 재구성했습니다.")
                        st.markdown(response.text)
                        
                        with st.expander("ℹ️ AI 답변에 대한 주의사항"):
                            st.warning("""
                            **중요:** 
                            - AI 답변은 등록된 지식 자료를 바탕으로 생성됩니다
                            - 의료적 판단이 필요한 경우 반드시 의료진과 상담하세요
                            - 응급상황에서는 기존 프로토콜을 우선 적용하세요
                            """)
                        
                        current_usage = load_usage()["count"]
                        st.info(f"💡 오늘 AI 사용량: {current_usage}/1,500 (무료)")
                        
                    except Exception as e:
                        st.error(f"AI 답변 생성 실패: {e}")
                        st.info("AI 답변 생성에 실패했지만, 아래 검색된 자료를 확인하세요.")
            
            elif not use_gemini:
                st.info("🤖 AI 답변 기능을 활성화하려면 아래를 확인하세요:")
                with st.expander("🤖 AI 답변 기능 활성화하기"):
                    st.markdown("""
                    **Gemini 1.5 Flash AI 답변 기능을 사용하려면:**
                    
                    1. **Google AI Studio**에서 무료 API 키 발급
                       - https://makersuite.google.com/app/apikey 접속
                       - "Create API key" 클릭
                       - API 키 복사
                    
                    2. **Streamlit Secrets 설정**
                       - 앱 관리자에게 다음 정보 전달:
                       ```
                       GOOGLE_API_KEY = "발급받은_API_키"
                       ```
                    
                    3. **사용량**: 일일 1,500회 무료
                    4. **기능**: 검색된 자료를 AI가 종합하여 맞춤 답변 생성
                    """)
            
            elif load_usage()["count"] >= 1500:
                st.warning("🚫 오늘의 AI 사용량을 모두 소진했습니다. 내일 다시 이용해주세요.")
            
            # 3단계: 원본 검색 결과 표시
            st.markdown("### 📋 검색된 원본 자료")
            for i, doc in enumerate(results):
                with st.expander(f"📄 {doc['title']} - {doc['category']} ({doc.get('score', 0)}점)"):
                    st.markdown(doc['content'])
                    if doc.get('tags'):
                        st.caption(f"태그: {doc['tags']}")
        else:
            st.warning("관련 자료를 찾을 수 없습니다.")
            st.info("💡 새로운 지식을 추가해서 데이터베이스를 확장해보세요!")

elif mode == "📝 지식 추가":
    st.header("📝 지식 추가")
    security_input = st.text_input("보안 코드:", type="password", key="add_security")
    
    if security_input == SECURITY_CODE:
        st.success("✅ 승인됨")
        with st.form("add_form"):
            title = st.text_input("제목:")
            category = st.selectbox("카테고리:", ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"])
            content = st.text_area("내용:", height=200)
            tags = st.text_input("태그:")
            
            if st.form_submit_button("➕ 추가") and title and content:
                add_knowledge(title, content, category, tags)
                st.success("✅ 추가 완료!")
                st.balloons()
    elif security_input:
        st.error("❌ 잘못된 코드")
    else:
        st.info("💡 보안 코드를 입력하세요 (관리자에게 문의)")

elif mode == "📚 지식 검색":
    st.header("📚 지식 검색")
    search_term = st.text_input("검색어:")
    
    if search_term:
        results = search_knowledge(search_term)
        if results:
            st.success(f"🔍 {len(results)}개 결과")
            for doc in results:
                with st.expander(f"📄 {doc['title']} - {doc['category']} ({doc['score']}점)"):
                    st.markdown(doc['content'])
                    if doc.get('tags'):
                        st.caption(f"태그: {doc['tags']}")
        else:
            st.warning("검색 결과 없음")

elif mode == "✏️ 지식 편집":
    st.header("✏️ 지식 편집")
    all_docs = get_all_knowledge()
    
    if all_docs:
        doc_titles = [f"{doc['title']} ({doc['category']})" for doc in all_docs]
        selected_idx = st.selectbox("편집할 지식:", range(len(doc_titles)), format_func=lambda x: doc_titles[x])
        selected_doc = all_docs[selected_idx]
        
        security_edit = st.text_input("편집 코드:", type="password", key="edit_security")
        
        if security_edit == SECURITY_CODE:
            st.success("✅ 편집 권한 확인")
            with st.form("edit_form"):
                new_title = st.text_input("제목:", value=selected_doc['title'])
                new_category = st.selectbox("카테고리:", ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"],
                                           index=["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"].index(selected_doc['category']) if selected_doc['category'] in ["프로토콜", "안전수칙", "장비운용", "응급상황", "기타"] else 4)
                new_content = st.text_area("내용:", value=selected_doc['content'], height=200)
                new_tags = st.text_input("태그:", value=selected_doc.get('tags', ''))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 저장") and new_title and new_content:
                        update_knowledge(selected_doc['id'], new_title, new_content, new_category, new_tags)
                        st.success("✅ 수정 완료!")
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("🗑️ 삭제"):
                        delete_knowledge(selected_doc['id'])
                        st.success("🗑️ 삭제 완료!")
                        st.rerun()
        elif security_edit:
            st.error("❌ 잘못된 코드")
    else:
        st.info("편집할 지식이 없습니다.")

# 하단 정보
st.markdown("---")
st.markdown("### 💾 사용 안내")

# 백업 상태 추가
if backup_info:
    # 자동 백업 상태 계산
    next_backup = st.session_state.get(AUTO_BACKUP_KEY, datetime.now()) + timedelta(minutes=AUTO_BACKUP_INTERVAL)
    time_until = next_backup - datetime.now()
    
    if time_until.total_seconds() > 0:
        minutes_left = int(time_until.total_seconds() / 60)
        auto_status = f"다음 자동백업: {minutes_left}분 후"
    else:
        auto_status = "자동백업 준비됨"
    
    st.info(f"""
**📅 현재 백업 상태**  
최종 백업: {backup_info['backup_time']} (서울시간) ({backup_info['total_docs']}개 문서)  
자동 백업: 30분 간격 활성화 ({auto_status})
""")
else:
    st.warning("⚠️ GitHub 백업이 없습니다. 백업을 권장합니다.")

st.markdown("""
- **🔄 자동 백업**: 30분마다 GitHub에 자동 백업 (토큰 설정 시)
- **🤖 AI 질의응답**: Gemini 1.5 Flash로 스마트한 답변 생성 (일일 1,500회 무료)
- **🔍 키워드 검색**: 등록된 지식에서 관련 자료 즉시 검색
- **리부트 시 보존**: 앱 시작 시 GitHub에서 자동 복원
- **수동 백업**: 사이드바 "백업" 버튼 클릭  
- **수동 복원**: 관리자 코드 입력 후 "복원" 버튼
- **보안 코드**: 지식 추가/편집 시 관리자에게 문의
""")
