import os
import json
import re
from datetime import datetime
from typing import List, Dict

# ChromaDB 환경 설정 (Streamlit Cloud 호환)
os.environ["CHROMA_SERVER_HOST"] = "localhost"
os.environ["ALLOW_RESET"] = "TRUE"

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("ChromaDB not available, using fallback storage")

class KnowledgeManager:
    def __init__(self):
        self.knowledge_dir = "./knowledge"
        os.makedirs(self.knowledge_dir, exist_ok=True)
        
        # ChromaDB 초기화 시도
        self.collection = None
        if CHROMADB_AVAILABLE:
            try:
                # Streamlit Cloud 호환 설정
                self.client = chromadb.PersistentClient(
                    path="./knowledge_db",
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                self.collection = self.client.get_or_create_collection("ct_knowledge")
                print("ChromaDB initialized successfully")
            except Exception as e:
                print(f"ChromaDB initialization failed: {e}, using fallback")
                self.collection = None
        
        # 백업 저장소 (JSON 파일)
        self.json_db_path = "./knowledge_backup.json"
        self.json_db = self._load_json_db()
        
        # 초기 실행시 기존 마크다운 파일들 로드
        self.load_existing_knowledge()
    
    def _load_json_db(self) -> Dict:
        """JSON 백업 데이터베이스 로드"""
        if os.path.exists(self.json_db_path):
            try:
                with open(self.json_db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading JSON DB: {e}")
        return {"documents": {}}
    
    def _save_json_db(self):
        """JSON 백업 데이터베이스 저장"""
        try:
            with open(self.json_db_path, 'w', encoding='utf-8') as f:
                json.dump(self.json_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving JSON DB: {e}")
    
    def add_knowledge(self, title: str, content: str, category: str, tags: str = "") -> bool:
        try:
            # 고유 ID 생성
            doc_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(title) % 10000}"
            
            # 메타데이터 준비
            metadata = {
                "title": title,
                "category": category,
                "tags": tags,
                "created_at": datetime.now().isoformat()
            }
            
            # ChromaDB에 추가 (가능한 경우)
            if self.collection is not None:
                try:
                    self.collection.add(
                        documents=[content],
                        metadatas=[metadata],
                        ids=[doc_id]
                    )
                except Exception as e:
                    print(f"ChromaDB add failed: {e}")
            
            # JSON 백업에 저장
            self.json_db["documents"][doc_id] = {
                "content": content,
                "metadata": metadata
            }
            self._save_json_db()
            
            # 마크다운 파일로 저장
            self._save_to_markdown(doc_id, title, content, category, tags)
            
            return True
        except Exception as e:
            print(f"Error adding knowledge: {e}")
            return False
    
    def get_all_knowledge(self) -> List[Dict]:
        """모든 지식 목록 가져오기"""
        try:
            knowledge_list = []
            
            # JSON 백업에서 가져오기
            for doc_id, data in self.json_db["documents"].items():
                metadata = data["metadata"]
                knowledge_list.append({
                    'id': doc_id,
                    'title': metadata['title'],
                    'content': data['content'],
                    'category': metadata['category'],
                    'tags': metadata.get('tags', ''),
                    'created_at': metadata.get('created_at', '')
                })
            
            # 생성일 순으로 정렬 (최신순)
            knowledge_list.sort(key=lambda x: x['created_at'], reverse=True)
            return knowledge_list
            
        except Exception as e:
            print(f"Error getting all knowledge: {e}")
            return []
    
    def update_knowledge(self, doc_id: str, title: str, content: str, category: str, tags: str = "") -> bool:
        """기존 지식 업데이트"""
        try:
            # 메타데이터 준비
            metadata = {
                "title": title,
                "category": category,
                "tags": tags,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # ChromaDB에서 업데이트 (가능한 경우)
            if self.collection is not None:
                try:
                    self.collection.delete(ids=[doc_id])
                    self.collection.add(
                        documents=[content],
                        metadatas=[metadata],
                        ids=[doc_id]
                    )
                except Exception as e:
                    print(f"ChromaDB update failed: {e}")
            
            # JSON 백업에서 업데이트
            self.json_db["documents"][doc_id] = {
                "content": content,
                "metadata": metadata
            }
            self._save_json_db()
            
            # 기존 마크다운 파일 업데이트
            self._update_markdown_file(doc_id, title, content, category, tags)
            
            return True
        except Exception as e:
            print(f"Error updating knowledge: {e}")
            return False
    
    def delete_knowledge(self, doc_id: str) -> bool:
        """지식 삭제"""
        try:
            # ChromaDB에서 삭제 (가능한 경우)
            if self.collection is not None:
                try:
                    self.collection.delete(ids=[doc_id])
                except Exception as e:
                    print(f"ChromaDB delete failed: {e}")
            
            # JSON 백업에서 삭제
            if doc_id in self.json_db["documents"]:
                del self.json_db["documents"][doc_id]
                self._save_json_db()
            
            # 마크다운 파일 삭제
            self._delete_markdown_file(doc_id)
            
            return True
        except Exception as e:
            print(f"Error deleting knowledge: {e}")
            return False
    
    def search_knowledge(self, query: str, n_results: int = 5) -> List[Dict]:
        try:
            # ChromaDB 벡터 검색 시도 (가능한 경우)
            if self.collection is not None:
                try:
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=n_results
                    )
                    
                    knowledge_list = []
                    if results['documents'] and results['documents'][0]:
                        for i in range(len(results['documents'][0])):
                            knowledge_list.append({
                                'id': results['ids'][0][i],
                                'title': results['metadatas'][0][i]['title'],
                                'content': results['documents'][0][i],
                                'category': results['metadatas'][0][i]['category'],
                                'tags': results['metadatas'][0][i].get('tags', ''),
                                'score': results['distances'][0][i] if 'distances' in results else 0
                            })
                    
                    if knowledge_list:
                        return knowledge_list
                except Exception as e:
                    print(f"ChromaDB search failed: {e}")
            
            # 키워드 검색으로 대체
            return self._keyword_search(query, n_results)
            
        except Exception as e:
            print(f"Error searching knowledge: {e}")
            return self._keyword_search(query, n_results)
    
    def _keyword_search(self, query: str, n_results: int = 5) -> List[Dict]:
        """키워드 기반 검색 (ChromaDB 대체)"""
        results = []
        query_lower = query.lower()
        
        try:
            for doc_id, data in self.json_db["documents"].items():
                metadata = data["metadata"]
                content = data["content"]
                
                # 제목, 내용, 태그에서 키워드 검색
                title_match = query_lower in metadata['title'].lower()
                content_match = query_lower in content.lower()
                tags_match = query_lower in metadata.get('tags', '').lower()
                category_match = query_lower in metadata['category'].lower()
                
                if title_match or content_match or tags_match or category_match:
                    # 점수 계산
                    score = 0
                    if title_match: score += 10
                    if content_match: score += 5
                    if tags_match: score += 8
                    if category_match: score += 6
                    
                    results.append({
                        'id': doc_id,
                        'title': metadata['title'],
                        'content': content,
                        'category': metadata['category'],
                        'tags': metadata.get('tags', ''),
                        'score': score
                    })
            
            # 점수 순으로 정렬하고 상위 n개 반환
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:n_results]
            
        except Exception as e:
            print(f"Error in keyword search: {e}")
            return []

    def _save_to_markdown(self, doc_id: str, title: str, content: str, category: str, tags: str):
        # 파일명에서 특수문자 제거
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        filename = f"{doc_id}_{safe_title}.md"
        filepath = os.path.join(self.knowledge_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"**카테고리:** {category}\n")
            f.write(f"**태그:** {tags}\n")
            f.write(f"**생성일:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(content)
    
    def _update_markdown_file(self, doc_id: str, title: str, content: str, category: str, tags: str):
        """마크다운 파일 업데이트"""
        try:
            # 기존 파일 찾기
            for filename in os.listdir(self.knowledge_dir):
                if filename.startswith(doc_id) and filename.endswith('.md'):
                    # 기존 파일 삭제
                    old_filepath = os.path.join(self.knowledge_dir, filename)
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                    break
            
            # 새 파일 생성
            self._save_to_markdown(doc_id, title, content, category, tags)
                
        except Exception as e:
            print(f"Error updating markdown file: {e}")
    
    def _delete_markdown_file(self, doc_id: str):
        """마크다운 파일 삭제"""
        try:
            for filename in os.listdir(self.knowledge_dir):
                if filename.startswith(doc_id) and filename.endswith('.md'):
                    filepath = os.path.join(self.knowledge_dir, filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    break
        except Exception as e:
            print(f"Error deleting markdown file: {e}")
    
    def load_existing_knowledge(self):
        """기존 마크다운 파일들을 로드"""
        if not os.path.exists(self.knowledge_dir):
            return
            
        for filename in os.listdir(self.knowledge_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(self.knowledge_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 기본 파싱
                    lines = content.split('\n')
                    title = lines[0].replace('# ', '') if lines else filename[:-3]
                    
                    # 메타데이터 추출
                    category = "기타"
                    tags = ""
                    content_start = 0
                    
                    for i, line in enumerate(lines):
                        if line.startswith('**카테고리:**'):
                            category = line.replace('**카테고리:**', '').strip()
                        elif line.startswith('**태그:**'):
                            tags = line.replace('**태그:**', '').strip()
                        elif line.strip() == '---':
                            content_start = i + 1
                            break
                    
                    # 실제 내용 추출
                    actual_content = '\n'.join(lines[content_start:]).strip()
                    
                    # 이미 존재하는지 확인
                    doc_id = filename[:-3]  # .md 제거
                    
                    if doc_id not in self.json_db["documents"]:
                        # JSON DB에 추가
                        metadata = {
                            "title": title,
                            "category": category,
                            "tags": tags,
                            "created_at": datetime.now().isoformat()
                        }
                        
                        self.json_db["documents"][doc_id] = {
                            "content": actual_content,
                            "metadata": metadata
                        }
                        
                        # ChromaDB에도 추가 (가능한 경우)
                        if self.collection is not None:
                            try:
                                self.collection.add(
                                    documents=[actual_content],
                                    metadatas=[metadata],
                                    ids=[doc_id]
                                )
                            except Exception as e:
                                print(f"ChromaDB add failed for {filename}: {e}")
                    
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
                    continue
        
        # JSON DB 저장
        self._save_json_db()
