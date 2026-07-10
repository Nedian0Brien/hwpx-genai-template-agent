from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TemplateMetadata:
    """
    [템플릿 메타데이터]
    벡터 DB(Qdrant)에 저장되고 검색될 문서 양식 정보
    """
    id: str                 # 고유 ID (UUID)
    filename: str           # 파일명 (예: vacation_v1.hwpx)
    description: str        # 문서 용도 설명 (임베딩 대상)
    field_schema: List[str] # 문서 내 존재하는 누름틀(Field) 이름 목록
    file_path: str          # 실제 파일 시스템 경로


@dataclass
class GenerationResult:
    """
    [문서 생성 결과]
    HwpxProcessor가 작업을 마친 후 반환하는 결과 객체
    """
    success: bool                   # 성공 여부
    output_path: str                # 생성된 파일 경로
    filled_fields: List[str]        # 성공적으로 채워진 필드 목록
    missing_fields: List[str]       # 요청했으나 문서에 없었던 필드 목록
    error_message: Optional[str] = None # 실패 시 에러 메시지
