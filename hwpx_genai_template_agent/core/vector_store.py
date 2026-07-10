import uuid
import os
from typing import List, Optional

from ..config import Config
from ..models import TemplateMetadata
from .hwpx_processor import HwpxProcessor

class TemplateRetriever:
    """
    [기억 모듈]
    공문서 양식(Template)을 벡터 DB에 저장하고, 
    사용자 자연어 쿼리와 가장 유사한 양식을 검색합니다.
    """

    def __init__(self):
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        self._qmodels = qmodels

        # 1. 임베딩 모델 로드 (LlamaIndex HuggingFaceEmbedding 사용)
        print(f"[Info] 임베딩 모델 로드 중: {Config.EMBEDDING_MODEL}")
        # [Changed] HuggingFaceEmbedding 초기화 (device 등 추가 설정 가능)
        self.encoder = HuggingFaceEmbedding(model_name=Config.EMBEDDING_MODEL)

        # 2. Qdrant 클라이언트 초기화 (로컬 파일 모드)
        self.client = QdrantClient(path=Config.VECTOR_DB_PATH)
        self.collection_name = Config.COLLECTION_NAME

        # 3. 컬렉션 존재 여부 확인 및 생성
        self._ensure_collection_exists()

        # 4. HWPX 처리기 (스키마 추출용)
        self.processor = HwpxProcessor()

    def _ensure_collection_exists(self):
        """컬렉션이 없으면 생성"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            # [Changed] 모델의 임베딩 차원 확인 (샘플 텍스트 사용)
            # HuggingFaceEmbedding 객체는 차원 정보를 직접 노출하지 않을 수 있어 샘플링 방식 사용
            sample_embedding = self.encoder.get_text_embedding("sample")
            vector_size = len(sample_embedding)
            
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=self._qmodels.VectorParams(
                    size=vector_size,
                    distance=self._qmodels.Distance.COSINE
                )
            )
            print(f"[Info] Qdrant 컬렉션 생성 완료: {self.collection_name} (Size: {vector_size})")

    def index_template(self, file_path: str, description: str) -> bool:
        """
        [저장] HWPX 파일을 분석하여 벡터 DB에 등록합니다.
        자동으로 내부 필드(Schema)를 추출하여 함께 저장합니다.
        """
        if not os.path.exists(file_path):
            print(f"[Error] 파일이 존재하지 않습니다: {file_path}")
            return False

        try:
            # 1. HWPX에서 필드명 추출 (HwpxProcessor 활용)
            field_schema = self.processor.extract_field_names(file_path)
            if not field_schema:
                print(f"[Warning] '{file_path}'에서 추출된 필드가 없습니다.")

            # 2. 파일명 및 ID 생성
            filename = os.path.basename(file_path)
            doc_id = str(uuid.uuid4())

            # 3. 설명(description) 임베딩
            # [Changed] encode() -> get_text_embedding() (리스트 변환 불필요, 이미 리스트 반환)
            embedding = self.encoder.get_text_embedding(description)

            # 4. Payload 구성 (메타데이터)
            payload = {
                "id": doc_id,
                "filename": filename,
                "description": description,
                "field_schema": field_schema,
                "file_path": os.path.abspath(file_path)
            }

            # 5. Qdrant 업로드
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    self._qmodels.PointStruct(
                        id=doc_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            print(f"[Success] 템플릿 인덱싱 완료: {filename} (ID: {doc_id})")
            return True

        except Exception as e:
            print(f"[Error] 템플릿 인덱싱 실패: {e}")
            return False

    def search(self, query: str, top_k: int = 1) -> Optional[TemplateMetadata]:
        """
        [검색] 사용자 질문과 가장 유사한 템플릿을 찾습니다.
        """
        # 1. 쿼리 벡터화
        # [Changed] encode() -> get_query_embedding()
        query_vector = self.encoder.get_query_embedding(query)

        # 2. Qdrant 검색
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )

        if not search_result:
            return None

        # 3. 가장 유사한 결과 1개 반환
        top_match = search_result[0]
        payload = top_match.payload

        # 4. Pydantic 모델로 변환하여 반환
        return TemplateMetadata(
            id=payload['id'],
            filename=payload['filename'],
            description=payload['description'],
            field_schema=payload['field_schema'],
            file_path=payload['file_path']
        )
