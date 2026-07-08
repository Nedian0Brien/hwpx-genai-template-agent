import zipfile
import xml.etree.ElementTree as ET
import os
import shutil
import tempfile

class Config:
    """
    [시스템 설정]
    HWPX 파일 구조 및 XML 네임스페이스 등 불변의 설정값을 관리합니다.
    """
    # -----------------------------------------------------------
    # [중요] HWPX XML 네임스페이스 정의
    # -----------------------------------------------------------
    NAMESPACES = {
        'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',  # 문단 관련
        'hc': 'http://www.hancom.co.kr/hwpml/2011/core',       # 핵심 코어
        'hm': 'http://www.hancom.co.kr/hwpml/2011/master-page',# 마스터 페이지
        'hp10': 'http://www.hancom.co.kr/hwpml/2016/paragraph',# 2016 버전 문단 확장
        'hpf': 'http://www.hancom.co.kr/hwpml/2011/footer',    # 꼬리말
        'hhs': 'http://www.hancom.co.kr/hwpml/2011/head-shape',# 머리말 모양
        'hch': 'http://www.hancom.co.kr/hwpml/2011/char-shape' # 글자 모양
    }
    
    # HWPX 내부 구조 설정
    XML_DIR = 'Contents'
    XML_FILE = 'section0.xml'

class DocumentCompleteTask:
    """
    [작업 설정]
    실제 문서 작성 작업에 필요한 데이터와 파일 경로를 정의합니다.
    작업별로 이 부분만 수정하면 됩니다.
    """
    # 테스트 파일 경로 설정
    DEFAULT_INPUT_FILE = "/content/sample_data/테스트용 문서.hwpx"
    DEFAULT_OUTPUT_FILE = "/content/output/completed_doc.hwpx"
    
    # 채워 넣을 데이터 (누름틀 필드명: 값)
    DATA = {
        "name": "홍길동",            # 필드명: name
        "department": "IT개발팀",    # 필드명: department
        "tel": "235-2223"            # 필드명: tel
    }

class HwpxFieldEditor:
    """
    HWPX 파일(공문서 양식)의 누름틀(Field) 값을 수정하는 클래스입니다.
    외부 라이브러리(pyhwpx 등) 없이 Python 표준 라이브러리만 사용합니다.
    """

    def __init__(self):
        # Config 클래스에서 네임스페이스 가져오기
        self.namespaces = Config.NAMESPACES

        # XML 라이브러리에 네임스페이스 등록
        # 이 과정이 없으면 저장된 XML 파일의 태그 앞에 'ns0:', 'ns1:' 같은 임의의 접두어가 붙어 파일이 손상될 수 있습니다.
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

    def _get_tag(self, prefix, tag_name):
        """
        네임스페이스 URL과 태그명을 결합하여 XML 검색용 태그 문자열을 생성합니다.
        예: prefix='hp', tag_name='p' -> '{http://www.hancom.co.kr/hwpml/2011/paragraph}p'
        """
        return f"{{{self.namespaces[prefix]}}}{tag_name}"

    def update_fields(self, input_path, output_path, field_data):
        """
        [메인 함수] 원본 HWPX 파일을 읽어 누름틀 값을 채운 뒤, 새로운 파일로 저장합니다.
        작업 완료 후 필드별 성공/실패 여부를 출력합니다.

        :param input_path: 원본 HWPX 템플릿 파일 경로
        :param output_path: 저장될 결과 HWPX 파일 경로
        :param field_data: 채워넣을 데이터 딕셔너리 (Key: 누름틀 필드명, Value: 변경할 값)
        """
        
        # 원본 파일 존재 여부 확인
        if not os.path.exists(input_path):
            print(f"[Error] 입력 파일이 존재하지 않습니다: {input_path}")
            return
            
        # 출력 디렉토리 확인 및 생성
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"[Info] 출력 디렉토리 생성: {output_dir}")
            except OSError as e:
                print(f"[Error] 출력 디렉토리 생성 실패: {e}")
                return

        updated_fields_set = set() # 실제 수정된 필드 목록을 저장할 변수

        # 임시 디렉토리 생성 (작업 후 자동 삭제됨)
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"[Info] 임시 작업 공간 생성: {temp_dir}")

            # 1. HWPX 압축 해제
            try:
                with zipfile.ZipFile(input_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            except zipfile.BadZipFile:
                print("[Error] 올바른 HWPX(ZIP) 파일이 아닙니다.")
                return

            # 2. 본문 XML 파일 찾기
            target_xml_path = os.path.join(temp_dir, Config.XML_DIR, Config.XML_FILE)
            
            if os.path.exists(target_xml_path):
                print(f"[Info] 본문 XML 수정 시작: {target_xml_path}")
                # XML 수정 실행 및 결과 반환
                updated_fields_set = self._modify_xml_content(target_xml_path, field_data)
            else:
                print("[Warning] 본문 파일(section0.xml)을 찾을 수 없습니다.")

            # 3. 수정된 내용을 다시 HWPX(ZIP)로 압축하여 저장
            self._create_hwpx_from_dir(temp_dir, output_path)
            print(f"[Success] 파일 생성이 완료되었습니다: {output_path}")
            
            # 4. 결과 리포트 출력
            self._print_result_report(field_data, updated_fields_set)

    def _modify_xml_content(self, xml_path, field_data):
        """
        실제 XML 파일을 열어서 누름틀(Field) 영역의 텍스트를 교체하는 핵심 로직입니다.
        구조의 깊이(Depth)에 상관없이 전체 요소를 순회하여 필드를 찾습니다.
        또한, 누름틀 내부의 안내 문구 스타일(빨간색 등)을 본문 스타일로 덮어씁니다.
        
        Returns:
            set: 실제로 값이 수정된 필드명들의 집합
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        updated_fields = set() # 실제 수정된 필드 기록용

        # 상태 변수 초기화
        current_field_name = None # 현재 처리 중인 누름틀 이름
        is_inside_field = False   # 타겟 누름틀 영역 안에 있는지 여부
        field_text_updated = False # 현재 누름틀의 텍스트를 이미 업데이트했는지 여부

        # [NEW] 스타일 추적을 위한 변수 추가
        last_run_element = None  # 가장 최근에 방문한 <hp:run> 요소
        target_style_id = None   # 누름틀 시작 위치의 스타일 ID (정상 스타일)

        # 문서의 모든 요소를 순서대로 순회 (XML 구조 깊이 무시)
        for element in root.iter():
            tag = element.tag

            # [NEW] 0. 실행(Run) 태그 추적
            if tag == self._get_tag('hp', 'run'):
                last_run_element = element

            # 1. 누름틀 시작 (<hp:fieldBegin>) 감지
            elif tag == self._get_tag('hp', 'fieldBegin'):
                field_name = element.get('name')
                
                # 우리가 찾던 필드인지 확인
                if field_name and field_name in field_data:
                    current_field_name = field_name
                    is_inside_field = True
                    field_text_updated = False
                    
                    # [NEW] 필드 시작점의 스타일 ID 캡처
                    # (fieldBegin이 포함된 run은 보통 정상 스타일을 가지고 있음)
                    if last_run_element is not None:
                        target_style_id = last_run_element.get('charPrIDRef')
                else:
                    is_inside_field = False
            
            # 2. 누름틀 끝 (<hp:fieldEnd>) 감지
            elif tag == self._get_tag('hp', 'fieldEnd'):
                # 현재 타겟 필드 안에 있었다면 상태 해제
                if is_inside_field:
                    is_inside_field = False
                    current_field_name = None
                    target_style_id = None # 스타일 타겟 초기화

            # 3. 텍스트 요소 (<hp:t>) 감지
            elif tag == self._get_tag('hp', 't'):
                # 타겟 필드 내부인 경우에만 내용 수정
                if is_inside_field and current_field_name:
                    
                    # [NEW] 텍스트 스타일 교체
                    # 현재 텍스트를 감싸고 있는 run의 스타일을 필드 시작점의 스타일로 덮어씌움
                    if last_run_element is not None and target_style_id is not None:
                        last_run_element.set('charPrIDRef', target_style_id)

                    if not field_text_updated:
                        # 첫 번째 텍스트 노드에 데이터 주입
                        new_value = str(field_data[current_field_name])
                        element.text = new_value
                        
                        field_text_updated = True
                        updated_fields.add(current_field_name) # 수정 성공 기록
                    else:
                        # 필드 내 텍스트가 여러 개로 쪼개져 있는 경우,
                        # 첫 번째 이후의 텍스트는 비워서 중복 표시 방지
                        element.text = ""

        # 수정된 XML 저장
        tree.write(xml_path, encoding='utf-8', xml_declaration=True)
        return updated_fields

    def _create_hwpx_from_dir(self, source_dir, output_path):
        """
        수정된 디렉토리(source_dir)를 다시 ZIP 포맷(.hwpx)으로 압축합니다.
        """
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)

    def _print_result_report(self, request_data, updated_fields):
        """
        작업 결과(성공/실패)를 콘솔에 보기 좋게 출력합니다.
        """
        print("\n" + "="*40)
        print("          [작업 결과 리포트]")
        print("="*40)
        
        success_list = []
        fail_list = []
        
        for key in request_data.keys():
            if key in updated_fields:
                success_list.append(key)
            else:
                fail_list.append(key)
                
        # 성공 항목 출력
        print(f"✅ 성공 ({len(success_list)}건):")
        if success_list:
            print(f"   - {', '.join(success_list)}")
        else:
            print("   - 없음")
            
        print("-" * 40)
        
        # 실패 항목 출력
        print(f"❌ 실패 ({len(fail_list)}건):")
        if fail_list:
            print(f"   - {', '.join(fail_list)}")
            print("   (원인: 문서 내에 해당 이름의 '누름틀'이 없습니다.)")
        else:
            print("   - 없음")
        print("="*40 + "\n")

# -----------------------------------------------------------
# [사용 예시] 이 파일을 직접 실행할 때 동작하는 코드
# -----------------------------------------------------------
if __name__ == "__main__":
    # 1. HWPX 수정기 인스턴스 생성
    editor = HwpxFieldEditor()

    # 2. DocumentCompleteTask 클래스에서 설정값 가져오기
    input_file = DocumentCompleteTask.DEFAULT_INPUT_FILE
    output_file = DocumentCompleteTask.DEFAULT_OUTPUT_FILE
    data = DocumentCompleteTask.DATA

    print("--- HWPX 자동화 시작 ---")
    
    # 3. 파일 존재 여부 체크 후 실행
    if os.path.exists(input_file):
        editor.update_fields(input_file, output_file, data)
    else:
        print(f"[Error] '{input_file}' 파일을 찾을 수 없습니다.")
        print("1. 한글 프로그램 실행")
        print("2. [입력] -> [필드 입력] -> [누름틀] 생성")
        print("3. 필드 이름을 DocumentCompleteTask.DATA의 키(name 등)와 맞춰주세요.")
        print("4. .hwpx 형식으로 저장 후 다시 실행해주세요.")