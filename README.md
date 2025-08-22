# 🏥 CT Room Staff Knowledge Management System

## 🌐 웹에서 바로 사용하기! (권장)

**👉 [여기를 클릭하여 웹에서 바로 사용](https://knowledge-for-ct-room-staff.streamlit.app)**
*(배포 후 실제 링크로 업데이트됩니다)*

### ⚡ 이미 GitHub 저장소가 준비되었습니다!

📁 **저장소**: https://github.com/radpushman/Knowledge_for_CT_Room_Staff

#### 바로 Streamlit Cloud 배포하기 (1분)
1. [share.streamlit.io](https://share.streamlit.io) 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. Repository: `radpushman/Knowledge_for_CT_Room_Staff`
5. Branch: `main`
6. Main file path: `app.py`
7. Deploy! 버튼 클릭

#### 시크릿 설정 (배포 후)
Streamlit Cloud 대시보드에서 Settings → Secrets:

```toml
# Google AI (선택사항 - 월 15회 무료)
GOOGLE_API_KEY = "your_google_gemini_api_key"

# GitHub 백업 (선택사항)
GITHUB_TOKEN = "your_github_token"
GITHUB_REPO = "radpushman/Knowledge_for_CT_Room_Staff"
```

## 🆓 완전 무료!

### 무료 구성 요소
- ✅ **Streamlit Cloud**: 무료 웹 호스팅 (3개 앱)
- ✅ **GitHub**: 무료 저장소 및 백업
- ✅ **ChromaDB**: 무료 AI 검색
- ✅ **키워드 검색**: 무제한 무료
- ⚠️ **Google Gemini API**: 월 15회 무료 (선택사항)

## 🌟 주요 기능

- 🤖 **AI 질의응답**: "심장 CT 촬영법이 뭐야?" 자연어 질문
- 🔍 **스마트 검색**: 키워드로 관련 자료 즉시 검색  
- 📝 **지식 추가**: 새로운 프로토콜, 경험 공유
- 💾 **자동 백업**: GitHub에 모든 지식 자동 저장
- 👥 **팀 협업**: 팀원들과 실시간 지식 공유
- 📱 **모바일 접근**: 스마트폰에서도 완벽 작동

## 🚀 배포 상태

### 현재 준비 완료:
- ✅ GitHub 저장소 생성됨
- ✅ 모든 코드 파일 준비됨
- ✅ requirements.txt 설정됨
- ⏳ Streamlit Cloud 배포 대기 중

### 다음 단계:
1. **즉시 배포**: share.streamlit.io에서 1분 내 배포
2. **시크릿 설정**: API 키 입력 (선택사항)
3. **팀 공유**: 웹 링크를 팀원들과 공유

## 📋 API 키 발급 가이드

### Google Gemini API (선택사항 - 무료)
1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. "Create API Key" 클릭
3. 생성된 키를 Streamlit Secrets에 추가

### GitHub Token (백업용 - 선택사항)
1. GitHub Settings → Developer settings → Personal access tokens
2. "Generate new token (classic)" 선택
3. `repo` 권한 체크
4. 토큰을 Streamlit Secrets에 추가

## 💡 사용 시나리오

### 👨‍⚕️ 의료진용
- "복부 CT에서 조영제 주입 시점은?"
- "응급 CT 촬영 시 주의사항"
- "소아 CT 촬영 프로토콜"

### 🔧 기술진용  
- "CT 장비 일일 점검 항목"
- "갠트리 오류 해결법"
- "조영제 주입기 문제 해결"

### 📚 교육용
- "신입 직원 교육 자료"
- "프로토콜 변경 사항"
- "안전 수칙 업데이트"

## 🌐 웹 배포 장점

### ⚡ 즉시 접근
- 병원 내 모든 컴퓨터에서 접근
- 휴대폰에서도 빠른 검색
- 설치 없이 웹브라우저만으로 사용

### 👥 팀 협업
- 실시간 지식 공유
- 모든 팀원이 동시 사용
- 새로운 지식 즉시 공유

### 💾 자동 백업
- GitHub 자동 동기화
- 데이터 손실 방지
- 버전 관리로 변경 이력 추적

## 🏃‍♂️ 로컬 실행 (개발용)

```bash
# 1. 저장소 클론
git clone https://github.com/radpushman/Knowledge_for_CT_Room_Staff.git
cd Knowledge_for_CT_Room_Staff

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 실행
streamlit run app.py
```

## 🛠️ 커스터마이징

### UI 개선
- 테마 색상 변경
- 로고 추가
- 레이아웃 조정

### 기능 확장
- 파일 업로드 기능
- 엑셀 데이터 가져오기
- 이미지 첨부 기능

## 🆘 문제 해결

### 배포 실패시
```bash
# 코드 업데이트 후 재시도
git add .
git commit -m "Fix deployment"
git push
```

### API 키 관련
- Google AI Studio에서 키 재발급
- Streamlit Secrets 재설정
- 브라우저 캐시 삭제

### 검색 문제
- 기본 지식 데이터 로드
- 키워드 변경해서 재검색
- 새 지식 추가 후 재시도

---

## 🎯 다음 단계

### 1️⃣ 즉시 배포 (1분)
👉 **[share.streamlit.io 에서 배포하기](https://share.streamlit.io)**

### 2️⃣ 팀 공유
- 배포 완료 후 웹 링크 획득
- CT실 팀원들과 링크 공유
- 모바일 북마크 추가 안내

### 3️⃣ 지식 구축
- 기본 CT 프로토콜 입력
- 자주 묻는 질문 추가
- 응급상황 대응 매뉴얼 등록

### 4️⃣ 활용 및 개선
- 팀원 피드백 수집
- 추가 기능 요청 검토
- 지속적인 지식 업데이트

**🚀 이제 바로 배포하여 CT실의 지식 관리를 혁신하세요!**
