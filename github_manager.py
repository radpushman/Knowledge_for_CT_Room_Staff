import requests
import base64
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import re

class GitHubManager:
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def backup_knowledge(self, title: str, content: str, category: str, tags: str) -> bool:
        """단일 지식을 GitHub에 백업"""
        try:
            # 파일명 생성 (안전한 파일명으로 변환)
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{safe_title}.md"
            
            # 마크다운 내용 생성
            md_content = f"""# {title}

**카테고리:** {category}
**태그:** {tags}
**생성일:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{content}
"""
            
            # GitHub에 파일 업로드
            path = f"knowledge/{filename}"
            return self._upload_file(path, md_content, f"Add knowledge: {title}")
            
        except Exception as e:
            print(f"Error backing up knowledge: {e}")
            return False
    
    def backup_all_knowledge(self, km) -> bool:
        """모든 지식을 GitHub에 백업"""
        try:
            # 로컬 knowledge 폴더의 모든 파일을 GitHub에 업로드
            knowledge_dir = "./knowledge"
            if not os.path.exists(knowledge_dir):
                return True
            
            success_count = 0
            total_files = 0
            
            for filename in os.listdir(knowledge_dir):
                if filename.endswith('.md'):
                    total_files += 1
                    filepath = os.path.join(knowledge_dir, filename)
                    
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    github_path = f"knowledge/{filename}"
                    if self._upload_file(github_path, content, f"Backup: {filename}"):
                        success_count += 1
            
            return success_count == total_files
            
        except Exception as e:
            print(f"Error backing up all knowledge: {e}")
            return False
    
    def sync_from_github(self) -> bool:
        """GitHub에서 최신 지식을 동기화"""
        try:
            # GitHub의 knowledge 폴더 내용 가져오기
            url = f"{self.base_url}/repos/{self.repo}/contents/knowledge"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                return False
            
            files = response.json()
            knowledge_dir = "./knowledge"
            os.makedirs(knowledge_dir, exist_ok=True)
            
            for file_info in files:
                if file_info['name'].endswith('.md'):
                    # 파일 내용 다운로드
                    file_response = requests.get(file_info['download_url'])
                    if file_response.status_code == 200:
                        local_path = os.path.join(knowledge_dir, file_info['name'])
                        with open(local_path, 'w', encoding='utf-8') as f:
                            f.write(file_response.text)
            
            return True
            
        except Exception as e:
            print(f"Error syncing from GitHub: {e}")
            return False
    
    def restore_all_knowledge(self, km) -> bool:
        """GitHub에서 모든 지식을 복원"""
        try:
            # 먼저 동기화
            if not self.sync_from_github():
                return False
            
            # JSON DB 초기화 및 재로드
            km.json_db = {"documents": {}, "last_updated": datetime.now().isoformat()}
            km._save_json_db()
            km.load_existing_knowledge()  # 새로 다운로드한 파일들 로드
            
            return True
            
        except Exception as e:
            print(f"Error restoring knowledge: {e}")
            return False
    
    def delete_knowledge_backup(self, filename: str) -> bool:
        """GitHub에서 지식 백업 파일 삭제"""
        try:
            path = f"knowledge/{filename}"
            url = f"{self.base_url}/repos/{self.repo}/contents/{path}"
            
            # 파일 정보 가져오기 (sha 필요)
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return False
            
            file_info = response.json()
            
            # 파일 삭제
            data = {
                "message": f"Delete knowledge: {filename}",
                "sha": file_info["sha"]
            }
            
            delete_response = requests.delete(url, headers=self.headers, json=data)
            return delete_response.status_code == 200
            
        except Exception as e:
            print(f"Error deleting knowledge backup: {e}")
            return False

    def get_repo_info(self) -> Optional[Dict]:
        """저장소 정보 가져오기"""
        try:
            url = f"{self.base_url}/repos/{self.repo}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                repo_data = response.json()
                return {
                    "name": repo_data["name"],
                    "description": repo_data.get("description", ""),
                    "created_at": repo_data["created_at"],
                    "updated_at": repo_data["updated_at"],
                    "size": repo_data["size"],
                    "language": repo_data.get("language", "Markdown"),
                    "private": repo_data["private"]
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting repo info: {e}")
            return None
    
    def _upload_file(self, path: str, content: str, commit_message: str) -> bool:
        """GitHub에 파일 업로드"""
        try:
            # 파일이 이미 존재하는지 확인
            url = f"{self.base_url}/repos/{self.repo}/contents/{path}"
            response = requests.get(url, headers=self.headers)
            
            # 파일 내용을 base64로 인코딩
            content_bytes = content.encode('utf-8')
            content_b64 = base64.b64encode(content_bytes).decode('utf-8')
            
            data = {
                "message": commit_message,
                "content": content_b64
            }
            
            # 파일이 존재하면 sha 추가 (업데이트용)
            if response.status_code == 200:
                existing_file = response.json()
                data["sha"] = existing_file["sha"]
            
            # 파일 업로드/업데이트
            upload_response = requests.put(url, headers=self.headers, json=data)
            return upload_response.status_code in [200, 201]
            
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False
