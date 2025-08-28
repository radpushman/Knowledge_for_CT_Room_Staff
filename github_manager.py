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
        self.last_error: Optional[str] = None  # 마지막 오류 메시지 저장

    def _set_error(self, where: str, response: Optional[requests.Response] = None, exc: Optional[Exception] = None):
        if response is not None:
            try:
                body = response.json()
            except Exception:
                body = response.text
            self.last_error = f"{where} failed: {response.status_code} {body}"
        elif exc is not None:
            self.last_error = f"{where} exception: {exc}"
        else:
            self.last_error = f"{where} failed"

    def get_last_error(self) -> Optional[str]:
        return self.last_error

    def backup_knowledge(self, title: str, content: str, category: str, tags: str) -> bool:
        """단일 지식을 GitHub에 백업"""
        try:
            # 먼저 knowledge 폴더가 있는지 확인하고 없으면 생성
            self._ensure_knowledge_folder()
            
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
            ok = self._upload_file(path, md_content, f"Add knowledge: {title}")
            if not ok:
                # _upload_file 내부에서 last_error 셋팅됨
                pass
            return ok
        except Exception as e:
            self._set_error("backup_knowledge", exc=e)
            return False
    
    def backup_all_knowledge(self, km) -> bool:
        """모든 지식을 GitHub에 백업"""
        try:
            self._ensure_knowledge_folder()
            knowledge_dir = "./knowledge"
            if not os.path.exists(knowledge_dir):
                return True
            
            success_count = 0
            total_files = 0
            
            for filename in os.listdir(knowledge_dir):
                # README.md 제외
                if filename.endswith('.md') and filename.lower() != "readme.md":
                    total_files += 1
                    filepath = os.path.join(knowledge_dir, filename)
                    
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    github_path = f"knowledge/{filename}"
                    if self._upload_file(github_path, content, f"Backup: {filename}"):
                        success_count += 1
            
            if total_files == 0:
                self.last_error = "No markdown files to backup in ./knowledge"
                return False
            
            ok = success_count == total_files
            if not ok:
                self.last_error = f"Backed up {success_count}/{total_files} files"
            return ok
            
        except Exception as e:
            self._set_error("backup_all_knowledge", exc=e)
            return False
    
    def sync_from_github(self) -> bool:
        """GitHub에서 최신 지식을 동기화"""
        try:
            # GitHub의 knowledge 폴더 내용 가져오기
            url = f"{self.base_url}/repos/{self.repo}/contents/knowledge"
            response = requests.get(url, headers=self.headers)
            
            print(f"GitHub API response status: {response.status_code}")
            
            if response.status_code == 404:
                self._set_error("sync_from_github", response)
                return False
            elif response.status_code != 200:
                self._set_error("sync_from_github", response)
                return False
            
            files = response.json()
            knowledge_dir = "./knowledge"
            os.makedirs(knowledge_dir, exist_ok=True)
            
            downloaded_count = 0
            
            for file_info in files:
                # README.md 파일은 건너뛰기 (대소문자 구분 없이)
                if (file_info['name'].endswith('.md') and 
                    file_info['name'].lower() != 'readme.md'):
                    try:
                        # 파일 내용 다운로드
                        file_response = requests.get(file_info['download_url'])
                        if file_response.status_code == 200:
                            local_path = os.path.join(knowledge_dir, file_info['name'])
                            with open(local_path, 'w', encoding='utf-8') as f:
                                f.write(file_response.text)
                            downloaded_count += 1
                            print(f"Downloaded: {file_info['name']}")
                        else:
                            self._set_error("download_file", file_response)
                    except Exception as e:
                        self._set_error("download_file", exc=e)
            
            print(f"Successfully downloaded {downloaded_count} knowledge files")
            if downloaded_count == 0:
                self.last_error = "No knowledge files found in GitHub/knowledge (excluding README.md)"
                return False
            
            return True
            
        except Exception as e:
            self._set_error("sync_from_github", exc=e)
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
            self._set_error("restore_all_knowledge", exc=e)
            return False
    
    def delete_knowledge_backup(self, doc_id: str) -> bool:
        """GitHub에서 지식 백업 파일 삭제 (ID로 파일 찾기)"""
        try:
            # GitHub의 knowledge 폴더에서 해당 ID로 시작하는 파일 찾기
            url = f"{self.base_url}/repos/{self.repo}/contents/knowledge"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                self._set_error("delete_knowledge_backup(list)", response)
                return False
            
            files = response.json()
            target_file = None
            
            # doc_id로 시작하는 마크다운 파일 찾기
            for file_info in files:
                if file_info['name'].startswith(doc_id) and file_info['name'].endswith('.md'):
                    target_file = file_info
                    break
            
            if not target_file:
                self.last_error = f"No backup file starting with {doc_id} found"
                return False
            
            # 파일 삭제
            delete_url = f"{self.base_url}/repos/{self.repo}/contents/knowledge/{target_file['name']}"
            data = {
                "message": f"Delete knowledge: {target_file['name']}",
                "sha": target_file["sha"]
            }
            
            delete_response = requests.delete(delete_url, headers=self.headers, json=data)
            if delete_response.status_code != 200:
                self._set_error("delete_knowledge_backup(delete)", delete_response)
                return False
            
            return True
            
        except Exception as e:
            self._set_error("delete_knowledge_backup", exc=e)
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
            else:
                self._set_error("get_repo_info", response)
            
            return None
            
        except Exception as e:
            self._set_error("get_repo_info", exc=e)
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
                data["sha"] = existing_file.get("sha")
            elif response.status_code not in (404, 200):
                # 조회 자체가 실패
                self._set_error("check_existing(_upload_file)", response)
                return False
            
            # 파일 업로드/업데이트
            upload_response = requests.put(url, headers=self.headers, json=data)
            ok = upload_response.status_code in [200, 201]
            if not ok:
                self._set_error("_upload_file(put)", upload_response)
            return ok
            
        except Exception as e:
            self._set_error("_upload_file", exc=e)
            return False

    def _ensure_knowledge_folder(self) -> bool:
        """knowledge 폴더가 없으면 생성"""
        try:
            # knowledge 폴더 확인
            url = f"{self.base_url}/repos/{self.repo}/contents/knowledge"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 404:
                # 폴더가 없으면 README.md 파일로 폴더 생성
                readme_content = """# 📚 CT실 지식 백업 폴더

이 폴더는 CT실 지식 관리 시스템의 백업 파일들이 저장되는 곳입니다.
"""
                
                readme_path = "knowledge/README.md"
                success = self._upload_file(readme_path, readme_content, "Create knowledge folder with README")
                if not success:
                    # _upload_file에서 last_error 셋팅됨
                    return False
                return True
            elif response.status_code == 200:
                return True
            else:
                self._set_error("_ensure_knowledge_folder", response)
                return False
            
        except Exception as e:
            self._set_error("_ensure_knowledge_folder", exc=e)
            return False

    def has_any_remote_knowledge(self) -> bool:
        """원격에 지식(MD 또는 JSON 스냅샷)이 존재하는지"""
        try:
            # JSON 스냅샷 확인
            if self.has_json_snapshot():
                return True
            # MD 파일 확인
            files = self.list_remote_files()
            return len(files) > 0
        except Exception as e:
            self._set_error("has_any_remote_knowledge", exc=e)
            return False

    def has_json_snapshot(self) -> bool:
        """원격에 knowledge_database.json 존재 여부"""
        try:
            url = f"{self.base_url}/repos/{self.repo}/contents/knowledge_database.json"
            resp = requests.get(url, headers=self.headers)
            return resp.status_code == 200
        except Exception as e:
            self._set_error("has_json_snapshot", exc=e)
            return False

    def backup_json_db(self, km) -> bool:
        """로컬 JSON DB를 원격에 스냅샷으로 백업"""
        try:
            content = json.dumps(km.json_db, ensure_ascii=False, indent=2)
            return self._upload_file("knowledge_database.json", content, "Backup knowledge_database.json")
        except Exception as e:
            self._set_error("backup_json_db", exc=e)
            return False

    def restore_json_db(self, km) -> bool:
        """원격 JSON 스냅샷을 로컬로 복원"""
        try:
            url = f"{self.base_url}/repos/{self.repo}/contents/knowledge_database.json"
            resp = requests.get(url, headers=self.headers)
            if resp.status_code != 200:
                self._set_error("restore_json_db", resp)
                return False
            meta = resp.json()
            download_url = meta.get("download_url")
            if not download_url:
                self.last_error = "No download_url for knowledge_database.json"
                return False
            raw = requests.get(download_url)
            if raw.status_code != 200:
                self._set_error("restore_json_db(download)", raw)
                return False
            # 로컬에 기록 + 메모리에 반영
            text = raw.text
            with open("./knowledge_database.json", "w", encoding="utf-8") as f:
                f.write(text)
            km.json_db = json.loads(text)
            km._save_json_db()
            return True
        except Exception as e:
            self._set_error("restore_json_db", exc=e)
            return False

    def list_remote_files(self) -> List[str]:
        """GitHub knowledge 폴더의 파일 목록(README 제외)"""
        try:
            url = f"{self.base_url}/repos/{self.repo}/contents/knowledge"
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                self._set_error("list_remote_files", response)
                return []
            files = response.json()
            return [f["name"] for f in files if f["name"].endswith(".md") and f["name"].lower() != "readme.md"]
        except Exception as e:
            self._set_error("list_remote_files", exc=e)
            return []
