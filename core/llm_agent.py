import json
import re
from typing import List, Dict, Any, Type
from openai import OpenAI
from pydantic import create_model, Field, ValidationError, BaseModel # [Added] Pydantic 모듈
from config import Config

class DataGenerator:
    """
    [두뇌 모듈]
    사용자의 자연어 요청(Query)과 템플릿의 스키마(Fields)를 결합하여,
    문서 작성을 위한 구조화된 JSON 데이터를 생성합니다.
    """

    def __init__(self):
        # [Changed] 내부망 LLM 연동을 위한 base_url 추가
        self.client = OpenAI(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_API_BASE
        )
        self.model = Config.LLM_MODEL

    def _create_dynamic_model(self, schema: List[str]) -> Type[BaseModel]:
        """
        [NEW] 런타임에 주어진 필드 목록(Schema)을 기반으로 Pydantic 모델 클래스를 동적 생성합니다.
        모든 필드는 문자열(str)이며, 누락 시 빈 문자열("")을 기본값으로 가집니다.
        """
        field_definitions = {
            field: (str, Field(default="", description=f"Value for {field}"))
            for field in schema
        }
        return create_model('DynamicHwpxModel', **field_definitions)

    def generate_field_data(self, user_query: str, schema: List[str]) -> Dict[str, str]:
        """
        LLM을 통해 자연어를 필드 데이터(JSON)로 변환합니다.
        Pydantic을 이용해 유효성을 검사하고, 실패 시 재시도(Retry)합니다.
        """
        if not schema:
            return {}

        # 1. Pydantic 동적 모델 생성
        DynamicModel = self._create_dynamic_model(schema)

        # 2. 시스템 프롬프트 구성
        system_prompt = (
            "당신은 공문서 작성 전문 행정 비서입니다.\n"
            "사용자의 요청을 분석하여 주어진 필드 목록(Schema)에 맞는 JSON 데이터를 생성하세요.\n\n"
            "[작성 규칙]\n"
            "1. 날짜 데이터는 한국 공문서 표준인 'YYYY. MM. DD.' 형식을 반드시 준수하세요. (예: 2024. 01. 01.)\n"
            "2. 주어진 필드 목록(Schema)에 있는 키(Key)만 사용하세요.\n"
            "3. 사용자의 요청 내용에 포함되지 않은 필드는 빈 문자열(\"\")로 채우세요.\n"
            "4. 불필요한 서술이나 마크다운 코드 블록(```json) 없이, 오직 순수한 JSON 문자열만 반환하세요."
        )

        user_message = (
            f"[필드 목록(Schema)]\n{', '.join(schema)}\n\n"
            f"[사용자 요청]\n\"{user_query}\"\n\n"
            "위 요청을 바탕으로 필드 목록을 채운 JSON 데이터를 작성해주세요."
        )

        # 대화 히스토리 초기화
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # [NEW] 재시도 루프 (Retry Loop)
        for attempt in range(Config.MAX_RETRIES):
            try:
                # 3. LLM API 호출
                print(f" [LLM] 데이터 생성 시도 {attempt + 1}/{Config.MAX_RETRIES}...")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1, # 약간의 유연성 부여
                    # response_format={"type": "json_object"} # 내부망 모델이 지원하지 않을 수 있어 주석 처리하거나 확인 필요
                )

                raw_content = response.choices[0].message.content
                
                # 4. JSON 파싱
                parsed_json = self._parse_json_response(raw_content)

                # 5. Pydantic 유효성 검사 (Validation)
                # 모델에 정의된 필드 타입과 구조에 맞는지 확인하고, 누락된 필드는 default("")로 채움
                validated_data = DynamicModel.model_validate(parsed_json)
                
                # 성공 시 dict 변환 후 반환
                return validated_data.model_dump()

            except ValidationError as e:
                # [Fail] 유효성 검사 실패 시 에러 메시지 구성
                error_msg = f"JSON 형식이 유효하지 않습니다. 다음 에러를 수정해서 다시 작성해주세요:\n{e}"
                print(f" [Retry] 검증 실패: {e}")
                
                # 대화 기록에 LLM의 잘못된 응답과 에러 메시지 추가 (Self-Correction 유도)
                messages.append({"role": "assistant", "content": raw_content})
                messages.append({"role": "user", "content": error_msg})

            except Exception as e:
                print(f" [Error] LLM 호출 중 예외 발생: {e}")
                # 치명적 에러면 재시도 없이 종료할 수도 있으나, 여기선 다음 시도로 진행
                if attempt == Config.MAX_RETRIES - 1:
                    break

        print(" [Warning] 최대 재시도 횟수 초과. 빈 데이터를 반환합니다.")
        return {field: "" for field in schema}

    def _parse_json_response(self, content: str) -> Dict[str, str]:
        """
        LLM 응답 문자열에서 JSON 객체를 안전하게 추출합니다.
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 마크다운 코드 블록 정규식 추출
            match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 단순 중괄호 추출
            match = re.search(r"(\{.*\})", content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 파싱 불가 시 빈 딕셔너리 반환하여 ValidationError 유도
            return {}