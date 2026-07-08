import os
import sys
from typing import List

# 모듈 경로 설정 (필요 시)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from core.hwpx_processor import HwpxProcessor
from core.vector_store import TemplateRetriever
from core.llm_agent import DataGenerator

def setup_directories():
    """필요한 디렉토리가 없으면 생성합니다."""
    os.makedirs('templates', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)

def auto_index_templates(retriever: TemplateRetriever):
    """
    'templates/' 폴더에 있는 HWPX 파일들을 스캔하여 벡터 DB에 자동 등록합니다.
    (간이 구현: 파일명을 설명(description)으로 사용)
    """
    template_dir = 'templates'
    if not os.path.exists(template_dir):
        return

    print("\n[Init] 템플릿 폴더 스캔 및 인덱싱 점검...")
    hwpx_files = [f for f in os.listdir(template_dir) if f.endswith('.hwpx') or f.endswith('.zip')]
    
    if not hwpx_files:
        print(f" [Warning] '{template_dir}' 폴더가 비어 있습니다. 테스트할 .hwpx 파일을 넣어주세요.")
        return

    count = 0
    for filename in hwpx_files:
        file_path = os.path.join(template_dir, filename)
        # 실제 운영 환경에서는 이미 인덱싱된 파일인지 체크하는 로직이 필요합니다.
        # 여기서는 편의상 매번 시도하며, Qdrant 내부 로직에 맡깁니다.
        
        # 파일명을 설명으로 사용하여 인덱싱
        description = os.path.splitext(filename)[0].replace("_", " ") + " 양식"
        success = retriever.index_template(file_path, description)
        if success:
            count += 1
    
    if count > 0:
        print(f" [Info] {count}개의 템플릿 처리 완료.")

def main():
    print("="*60)
    print("      📄 HWPX 공문서 자동 생성 AI 에이전트")
    print("="*60)

    # 1. 환경 설정 및 모듈 초기화
    setup_directories()
    
    try:
        processor = HwpxProcessor()
        retriever = TemplateRetriever()
        generator = DataGenerator()
    except Exception as e:
        print(f"\n[Critical Error] 시스템 초기화 실패: {e}")
        print("config.py의 설정(API KEY 등)을 확인해주세요.")
        return

    # 2. 템플릿 자동 학습 (로컬 파일)
    auto_index_templates(retriever)

    print("\n>>> 시스템 준비 완료. (종료하려면 'exit' 또는 'q' 입력)")

    # 3. 메인 루프
    while True:
        user_query = input("\n[사용자 요청] >> ").strip()
        
        if not user_query:
            continue
        if user_query.lower() in ['exit', 'q', 'quit']:
            print("시스템을 종료합니다.")
            break

        print("\n------------------------------------------------------------")
        print(" 1. 🔍 양식 검색 중... (RAG)")
        
        # (1) 검색 수행
        template_meta = retriever.search(user_query)
        
        if not template_meta:
            print(" [Fail] 적절한 양식을 찾지 못했습니다.")
            print(" -> templates 폴더에 관련 HWPX 파일이 있는지, 내용과 관련된 파일명인지 확인해주세요.")
            continue
            
        print(f" -> 선택된 양식: {template_meta.filename}")
        print(f" -> 양식 설명: {template_meta.description}")
        print(f" -> 감지된 필드: {template_meta.field_schema}")

        # (2) 데이터 생성
        print("\n 2. 🧠 데이터 생성 중... (LLM)")
        field_data = generator.generate_field_data(user_query, template_meta.field_schema)
        
        print(" -> 생성된 데이터(JSON):")
        for k, v in field_data.items():
            print(f"    - {k}: {v}")

        # (3) 문서 합성
        print("\n 3. 💾 문서 파일 생성 중... (Processing)")
        output_filename = f"result_{template_meta.filename}"
        output_path = os.path.join('output', output_filename)
        
        result = processor.fill_fields(template_meta.file_path, output_path, field_data)
        
        if result.success:
            print(f"\n [Success] 문서 생성이 완료되었습니다!")
            print(f" -> 저장 경로: {os.path.abspath(result.output_path)}")
            
            if result.missing_fields:
                print(f" [Info] 채워지지 않은 필드: {result.missing_fields}")
        else:
            print(f"\n [Error] 문서 생성 실패: {result.error_message}")
            
        print("------------------------------------------------------------")

if __name__ == "__main__":
    main()