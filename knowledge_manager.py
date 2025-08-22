import os
import json
import re
from datetime import datetime
from typing import List, Dict

class KnowledgeManager:
    def __init__(self):
        self.knowledge_dir = "./knowledge"
        os.makedirs(self.knowledge_dir, exist_ok=True)
        
        # JSON 기반 데이터베이스
        self.json_db_path = "./knowledge_database.json"
        self.json_db = self._load_json_db()
        
        # 초기 실행시 기존 마크다운 파일들 로드
        self.load_existing_knowledge()
        print("Knowledge Manager initialized with JSON database")
    
    def _load_json_db(self) -> Dict:
        """JSON 데이터베이스 로드"""
        if os.path.exists(self.json_db_path):
            try:
                with open(self.json_db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading JSON DB: {e}")
        return {"documents": {}, "last_updated": datetime.now().isoformat()}
    
    def _save_json_db(self):
        """JSON 데이터베이스 저장"""
        try:
            self.json_db["last_updated"] = datetime.now().isoformat()
            with open(self.json_db_path, 'w', encoding='utf-8') as f:
                json.dump(self.json_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving JSON DB: {e}")
    
    def add_knowledge(self, title: str, content: str, category: str, tags: str = "") -> bool:
        try:
            # 고유 ID 생성
            doc_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{abs(hash(title)) % 10000}"
            
            # 메타데이터 준비
            metadata = {
                "title": title,
                "category": category,
                "tags": tags,
                "created_at": datetime.now().isoformat()
            }
            
            # JSON 데이터베이스에 저장
            self.json_db["documents"][doc_id] = {
                "content": content,
                "metadata": metadata
            }
            self._save_json_db()
            
            # 마크다운 파일로 저장
            self._save_to_markdown(doc_id, title, content, category, tags)
            
            print(f"Added knowledge: {title}")
            return True
        except Exception as e:
            print(f"Error adding knowledge: {e}")
            return False
    
    def get_all_knowledge(self) -> List[Dict]:
        """모든 지식 목록 가져오기"""
        try:
            knowledge_list = []
            
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
            # 기존 생성일 유지
            old_created_at = self.json_db["documents"].get(doc_id, {}).get("metadata", {}).get("created_at", datetime.now().isoformat())
            
            # 메타데이터 준비
            metadata = {
                "title": title,
                "category": category,
                "tags": tags,
                "created_at": old_created_at,
                "updated_at": datetime.now().isoformat()
            }
            
            # JSON 데이터베이스에서 업데이트
            self.json_db["documents"][doc_id] = {
                "content": content,
                "metadata": metadata
            }
            self._save_json_db()
            
            # 기존 마크다운 파일 업데이트
            self._update_markdown_file(doc_id, title, content, category, tags)
            
            print(f"Updated knowledge: {title}")
            return True
        except Exception as e:
            print(f"Error updating knowledge: {e}")
            return False
    
    def delete_knowledge(self, doc_id: str) -> bool:
        """지식 삭제"""
        try:
            # JSON 데이터베이스에서 삭제
            if doc_id in self.json_db["documents"]:
                title = self.json_db["documents"][doc_id]["metadata"]["title"]
                del self.json_db["documents"][doc_id]
                self._save_json_db()
                print(f"Deleted knowledge: {title}")
            
            # 마크다운 파일 삭제
            self._delete_markdown_file(doc_id)
            
            return True
        except Exception as e:
            print(f"Error deleting knowledge: {e}")
            return False
    
    def search_knowledge(self, query: str, n_results: int = 5) -> List[Dict]:
        """키워드 기반 지식 검색"""
        try:
            return self._smart_search(query, n_results)
        except Exception as e:
            print(f"Error searching knowledge: {e}")
            return []
    
    def _smart_search(self, query: str, n_results: int = 5) -> List[Dict]:
        """향상된 키워드 검색"""
        results = []
        query_lower = query.lower()
        query_words = [word.strip() for word in query_lower.split() if len(word.strip()) > 1]
        
        try:
            for doc_id, data in self.json_db["documents"].items():
                metadata = data["metadata"]
                content = data["content"]
                
                # 검색 점수 계산
                score = 0
                
                # 1. 제목에서 검색
                title_lower = metadata['title'].lower()
                for word in query_words:
                    if word in title_lower:
                        score += 15  # 제목 매치는 높은 점수
                
                # 2. 전체 제목이 쿼리를 포함하는 경우
                if query_lower in title_lower:
                    score += 20
                
                # 3. 카테고리에서 검색
                category_lower = metadata['category'].lower()
                if query_lower in category_lower:
                    score += 10
                
                # 4. 태그에서 검색
                tags_lower = metadata.get('tags', '').lower()
                for word in query_words:
                    if word in tags_lower:
                        score += 12
                
                # 5. 내용에서 검색
                content_lower = content.lower()
                content_matches = 0
                for word in query_words:
                    content_matches += content_lower.count(word)
                score += min(content_matches * 3, 15)  # 내용 매치, 최대 15점
                
                # 6. 전체 쿼리가 내용에 있는 경우
                if query_lower in content_lower:
                    score += 8
                
                # 점수가 있는 경우만 결과에 포함
                if score > 0:
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
            print(f"Error in smart search: {e}")
            return []

    def _save_to_markdown(self, doc_id: str, title: str, content: str, category: str, tags: str):
        # 파일명에서 특수문자 제거
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)[:50]  # 길이 제한
        filename = f"{doc_id}_{safe_title}.md"
        filepath = os.path.join(self.knowledge_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**카테고리:** {category}\n")
                f.write(f"**태그:** {tags}\n")
                f.write(f"**생성일:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(content)
        except Exception as e:
            print(f"Error saving markdown file: {e}")
    
    def _update_markdown_file(self, doc_id: str, title: str, content: str, category: str, tags: str):
        """마크다운 파일 업데이트"""
        try:
            # 기존 파일 찾아서 삭제
            if os.path.exists(self.knowledge_dir):
                for filename in os.listdir(self.knowledge_dir):
                    if filename.startswith(doc_id) and filename.endswith('.md'):
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
            if os.path.exists(self.knowledge_dir):
                for filename in os.listdir(self.knowledge_dir):
                    if filename.startswith(doc_id) and filename.endswith('.md'):
                        filepath = os.path.join(self.knowledge_dir, filename)
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        break
        except Exception as e:
            print(f"Error deleting markdown file: {e}")
    
    def load_existing_knowledge(self):
        """기존 마크다운 파일들을 JSON DB로 로드"""
        if not os.path.exists(self.knowledge_dir):
            return
            
        loaded_count = 0
        
        try:
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
                        doc_id = filename.replace('.md', '')
                        
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
                            loaded_count += 1
                        
                    except Exception as e:
                        print(f"Error loading {filename}: {e}")
                        continue
            
            if loaded_count > 0:
                self._save_json_db()
                print(f"Loaded {loaded_count} existing knowledge files")
                
        except Exception as e:
            print(f"Error in load_existing_knowledge: {e}")
    
    def get_stats(self) -> Dict:
        """지식 데이터베이스 통계"""
        try:
            total_docs = len(self.json_db["documents"])
            categories = {}
            
            for doc_data in self.json_db["documents"].values():
                category = doc_data["metadata"]["category"]
                categories[category] = categories.get(category, 0) + 1
            
            return {
                "total_documents": total_docs,
                "categories": categories,
                "last_updated": self.json_db.get("last_updated", "N/A")
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"total_documents": 0, "categories": {}, "last_updated": "N/A"}
