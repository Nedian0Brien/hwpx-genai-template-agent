import zipfile
import xml.etree.ElementTree as ET
import os
import shutil
import tempfile
from typing import List, Dict, Set
from ..config import Config
from ..models import GenerationResult

class HwpxProcessor:
    """
    HWPX 파일을 파싱하고 데이터를 주입하는 핵심 엔진 클래스.
    읽기(필드 추출)와 쓰기(데이터 채우기) 기능을 모두 담당합니다.
    """

    def __init__(self):
        self.namespaces = Config.NAMESPACES
        # XML 라이브러리에 네임스페이스 등록
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

    def _get_tag(self, prefix: str, tag_name: str) -> str:
        """네임스페이스 URL과 태그명을 결합하여 XML 검색용 태그 문자열 생성"""
        return f"{{{self.namespaces[prefix]}}}{tag_name}"

    def extract_field_names(self, file_path: str) -> List[str]:
        """
        [전처리용] HWPX 파일을 읽어 존재하는 모든 누름틀(Field)의 이름을 리스트로 반환.
        Qdrant에 스키마를 등록할 때 사용됨.
        """
        field_names = set()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        # 임시 디렉토리에서 작업
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                xml_path = os.path.join(temp_dir, Config.XML_DIR, Config.XML_FILE)
                
                if os.path.exists(xml_path):
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    
                    # 모든 요소 순회하며 fieldBegin 태그 찾기
                    for element in root.iter():
                        if element.tag == self._get_tag('hp', 'fieldBegin'):
                            name = element.get('name')
                            if name:
                                field_names.add(name)
            except Exception as e:
                print(f"[Error] 필드 추출 중 오류 발생: {e}")
                return []

        return list(field_names)

    def fill_fields(self, template_path: str, output_path: str, data: Dict[str, str]) -> GenerationResult:
        """
        [생성용] 템플릿 파일에 데이터를 채워 새로운 HWPX 파일을 생성.
        """
        # 결과 객체 초기화
        result = GenerationResult(
            success=False,
            output_path=output_path,
            filled_fields=[],
            missing_fields=[],
            error_message=None
        )

        if not os.path.exists(template_path):
            result.error_message = f"템플릿 파일 없음: {template_path}"
            return result

        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        updated_fields_set = set()

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. 압축 해제
                with zipfile.ZipFile(template_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # 2. XML 수정
                xml_path = os.path.join(temp_dir, Config.XML_DIR, Config.XML_FILE)
                if os.path.exists(xml_path):
                    updated_fields_set = self._modify_xml_content(xml_path, data)
                
                # 3. 재압축
                self._create_hwpx_from_dir(temp_dir, output_path)
                
                result.success = True
                result.filled_fields = list(updated_fields_set)
                
                # 요청했으나 채워지지 않은 필드 계산
                all_requested_keys = set(data.keys())
                result.missing_fields = list(all_requested_keys - updated_fields_set)

            except Exception as e:
                result.success = False
                result.error_message = str(e)

        return result

    def _modify_xml_content(self, xml_path: str, field_data: Dict[str, str]) -> Set[str]:
        """XML 내용을 실제로 수정하고 수정된 필드 목록 반환"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        updated_fields = set()
        
        current_field_name = None
        is_inside_field = False
        field_text_updated = False
        
        # 스타일 보정을 위한 추적 변수
        last_run_element = None
        target_style_id = None

        for element in root.iter():
            tag = element.tag

            # <hp:run> 추적
            if tag == self._get_tag('hp', 'run'):
                last_run_element = element

            # <hp:fieldBegin>
            elif tag == self._get_tag('hp', 'fieldBegin'):
                field_name = element.get('name')
                if field_name and field_name in field_data:
                    current_field_name = field_name
                    is_inside_field = True
                    field_text_updated = False
                    
                    if last_run_element is not None:
                        target_style_id = last_run_element.get('charPrIDRef')
                else:
                    is_inside_field = False
            
            # <hp:fieldEnd>
            elif tag == self._get_tag('hp', 'fieldEnd'):
                if is_inside_field:
                    is_inside_field = False
                    current_field_name = None
                    target_style_id = None

            # <hp:t> (텍스트)
            elif tag == self._get_tag('hp', 't'):
                if is_inside_field and current_field_name:
                    # 스타일 보정
                    if last_run_element is not None and target_style_id is not None:
                        last_run_element.set('charPrIDRef', target_style_id)

                    if not field_text_updated:
                        element.text = str(field_data[current_field_name])
                        field_text_updated = True
                        updated_fields.add(current_field_name)
                    else:
                        element.text = "" # 중복 텍스트 제거

        tree.write(xml_path, encoding='utf-8', xml_declaration=True)
        return updated_fields

    def _create_hwpx_from_dir(self, source_dir: str, output_path: str):
        """디렉토리를 HWPX(ZIP)로 압축"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
