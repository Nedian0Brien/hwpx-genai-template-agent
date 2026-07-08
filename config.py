import os

class Config:
    """
    [시스템 설정]
    HWPX 구조, 벡터 DB, 그리고 LLM 설정을 통합 관리합니다.
    """
    # -----------------------------------------------------------
    # [중요] HWPX XML 네임스페이스 정의
    # -----------------------------------------------------------
    NAMESPACES = {
        'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',   # 문단 관련
        'hc': 'http://www.hancom.co.kr/hwpml/2011/core',        # 핵심 코어
        'hm': 'http://www.hancom.co.kr/hwpml/2011/master-page', # 마스터 페이지
        'hp10': 'http://www.hancom.co.kr/hwpml/2016/paragraph', # 2016 버전 문단 확장
        'hpf': 'http://www.hancom.co.kr/hwpml/2011/footer',     # 꼬리말
        'hhs': 'http://www.hancom.co.kr/hwpml/2011/head-shape', # 머리말 모양
        'hch': 'http://www.hancom.co.kr/hwpml/2011/char-shape'  # 글자 모양
    }
    
    # HWPX 내부 구조 설정
    XML_DIR = 'Contents'
    XML_FILE = 'section0.xml'

    # -----------------------------------------------------------
    # [Memory] 벡터 DB 설정
    # -----------------------------------------------------------
    VECTOR_DB_PATH = os.getenv('HWPX_VECTOR_DB_PATH', './qdrant_db')
    COLLECTION_NAME = os.getenv('HWPX_COLLECTION_NAME', 'hwpx_templates')
    EMBEDDING_MODEL = os.getenv('HWPX_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')

    # -----------------------------------------------------------
    # [Brain] LLM 설정
    # -----------------------------------------------------------
    LLM_API_KEY = os.getenv('HWPX_LLM_API_KEY', '')
    LLM_API_BASE = os.getenv('HWPX_LLM_API_BASE', '')
    LLM_MODEL = os.getenv('HWPX_LLM_MODEL', '')
    MAX_RETRIES = int(os.getenv('HWPX_LLM_MAX_RETRIES', '3'))
