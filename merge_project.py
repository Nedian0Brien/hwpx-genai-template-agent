import os

def merge_files(output_filename="merged_code.txt"):
    """
    현재 디렉토리 하위의 모든 .py, .md 파일을 찾아 하나의 파일로 병합합니다.
    """
    # 합칠 대상 확장자
    target_exts = {'.py', '.md'}
    
    # 탐색에서 제외할 폴더명
    exclude_dirs = {'qdrant_db', 'output', 'templates', 'venv', '__pycache__', '.git', '.idea'}

    current_script = os.path.basename(__file__)

    with open(output_filename, 'w', encoding='utf-8') as outfile:
        # os.walk로 하위 디렉토리까지 재귀 탐색
        for root, dirs, files in os.walk("."):
            # 제외할 디렉토리는 탐색 리스트에서 제거 (in-place 수정)
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                # 1. 확장자 확인
                _, ext = os.path.splitext(file)
                if ext not in target_exts:
                    continue
                
                # 2. 자기 자신(이 스크립트)과 결과 파일은 제외
                if file == current_script or file == output_filename:
                    continue

                # 3. 파일 경로 생성 (예: core/hwpx_processor.py)
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, ".")

                # 4. 파일 내용 읽기 및 쓰기
                try:
                    with open(full_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        
                        # 구분자 및 내용 작성
                        outfile.write(f"\n{'='*30}\n")
                        outfile.write(f"File: {relative_path}\n")
                        outfile.write(f"{'='*30}\n\n")
                        outfile.write(content)
                        outfile.write("\n\n") # 파일 간 간격
                        
                    print(f"[Added] {relative_path}")
                except Exception as e:
                    print(f"[Skip] {relative_path} (Error: {e})")

    print(f"\n[Done] 모든 파일이 '{output_filename}'에 저장되었습니다.")

if __name__ == "__main__":
    merge_files()