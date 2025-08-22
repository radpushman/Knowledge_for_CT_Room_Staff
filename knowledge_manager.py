import chromadb
import os
import json
import re
from datetime import datetime
from typing import List, Dict

class KnowledgeManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./knowledge_db")
        self.collection = self.client.get_or_create_collection("ct_knowledge")
        self.knowledge_dir = "./knowledge"
        os.makedirs(self.knowledge_dir, exist_ok=True)
        
        # 초기 실행시 기존 마크다운 파일들 로드
        self.load_existing_knowledge()
    
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
            
            # ChromaDB에 추가
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            # 마크다운 파일로 저장
            self._save_to_markdown(doc_id, title, content, category, tags)
            
            return True
        except Exception as e:
            print(f"Error adding knowledge: {e}")
            return False
    
    def get_all_knowledge(self) -> List[Dict]:
        """모든 지식 목록 가져오기"""
        try:
            all_docs = self.collection.get()
            
            knowledge_list = []
            for i, doc in enumerate(all_docs['documents']):
                metadata = all_docs['metadatas'][i]
                doc_id = all_docs['ids'][i]
                
                knowledge_list.append({
                    'id': doc_id,
                    'title': metadata['title'],
                    'content': doc,
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
            
            # ChromaDB에서 업데이트 (삭제 후 재추가)
            self.collection.delete(ids=[doc_id])
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            # 기존 마크다운 파일 업데이트
            self._update_markdown_file(doc_id, title, content, category, tags)
            
            return True
        except Exception as e:
            print(f"Error updating knowledge: {e}")
            return False
    
    def delete_knowledge(self, doc_id: str) -> bool:
        """지식 삭제"""
        try:
            # ChromaDB에서 삭제
            self.collection.delete(ids=[doc_id])
            
            # 마크다운 파일 삭제
            self._delete_markdown_file(doc_id)
            
            return True
        except Exception as e:
            print(f"Error deleting knowledge: {e}")
            return False
    
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
            
            # 새 파일명 생성
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            filename = f"{doc_id}_{safe_title}.md"
            filepath = os.path.join(self.knowledge_dir, filename)
            
            # 새 파일 생성
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**카테고리:** {category}\n")
                f.write(f"**태그:** {tags}\n")
                f.write(f"**수정일:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(content)
                
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

    def search_knowledge(self, query: str, n_results: int = 5) -> List[Dict]:
        try:
            # ChromaDB 벡터 검색 시도
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            knowledge_list = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    knowledge_list.append({
                        'id': results['ids'][0][i],  # ID 추가
                        'title': results['metadatas'][0][i]['title'],
                        'content': results['documents'][0][i],
                        'category': results['metadatas'][0][i]['category'],
                        'tags': results['metadatas'][0][i].get('tags', ''),
                        'score': results['distances'][0][i] if 'distances' in results else 0
                    })
            
            # 벡터 검색이 실패하거나 결과가 없으면 키워드 검색으로 대체
            if not knowledge_list:
                knowledge_list = self._keyword_search(query, n_results)
            
            return knowledge_list
        except Exception as e:
            print(f"Error searching knowledge: {e}")
            # 벡터 검색 실패시 키워드 검색으로 대체
            return self._keyword_search(query, n_results)
    
    def _keyword_search(self, query: str, n_results: int = 5) -> List[Dict]:
        """무료 키워드 기반 검색"""
        results = []
        query_lower = query.lower()
        
        # 모든 문서 가져오기
        try:
            all_docs = self.collection.get()
            
            for i, doc in enumerate(all_docs['documents']):
                metadata = all_docs['metadatas'][i]
                doc_id = all_docs['ids'][i]
                
                # 제목, 내용, 태그에서 키워드 검색
                title_match = query_lower in metadata['title'].lower()
                content_match = query_lower in doc.lower()
                tags_match = query_lower in metadata.get('tags', '').lower()
                category_match = query_lower in metadata['category'].lower()
                
                if title_match or content_match or tags_match or category_match:
                    # 점수 계산 (제목 매치가 가장 높은 점수)
                    score = 0
                    if title_match: score += 10
                    if content_match: score += 5
                    if tags_match: score += 8
                    if category_match: score += 6
                    
                    results.append({
                        'id': doc_id,  # ID 추가
                        'title': metadata['title'],
                        'content': doc,
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
    
    def load_existing_knowledge(self):
        """기존 마크다운 파일들을 ChromaDB로 로드"""
        if not os.path.exists(self.knowledge_dir):
            return
            
        for filename in os.listdir(self.knowledge_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(self.knowledge_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 기본 파싱 (더 정교한 파싱 가능)
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
                    
                    # 이미 존재하는지 확인 (중복 방지)
                    doc_id = filename[:-3]  # .md 제거
                    
                    try:
                        self.collection.get(ids=[doc_id])
                        # 이미 존재하면 스킵
                        continue
                    except:
                        # 존재하지 않으면 추가
                        pass
                    
                    # ChromaDB에 추가
                    metadata = {
                        "title": title,
                        "category": category,
                        "tags": tags,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    self.collection.add(
                        documents=[actual_content],
                        metadatas=[metadata],
                        ids=[doc_id]
                    )
                    
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
                    continue
