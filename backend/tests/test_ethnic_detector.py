"""民族关键词检测测试。"""
from app.utils.ethnic_detector import infer_ethnic, needs_retrieval, is_symptom_related


class TestInferEthnic:
    def test_tibetan_keywords(self):
        assert infer_ethnic("藏医有什么特色疗法") == "藏族"
        assert infer_ethnic("藏药的分类") == "藏族"
        assert infer_ethnic("藏族医学历史") == "藏族"

    def test_qiang_keywords(self):
        assert infer_ethnic("羌医的诊断方法") == "羌族"
        assert infer_ethnic("羌药方剂") == "羌族"

    def test_yi_keywords(self):
        assert infer_ethnic("彝医的治疗") == "彝族"
        assert infer_ethnic("彝族药方") == "彝族"

    def test_default_to_tibetan(self):
        assert infer_ethnic("什么是民族医药") == "藏族"
        assert infer_ethnic("你好") == "藏族"

    def test_empty_query(self):
        assert infer_ethnic("") == "藏族"


class TestNeedsRetrieval:
    def test_professional_model_with_ethnic_keywords(self):
        assert needs_retrieval("藏医有什么疗法", "专业模型") is True
        assert needs_retrieval("羌药分类", "专业模型") is True

    def test_living_model_no_retrieval(self):
        assert needs_retrieval("藏医有什么疗法", "生活模型") is False

    def test_no_ethnic_keywords(self):
        assert needs_retrieval("今天天气怎么样", "专业模型") is False


class TestIsSymptomRelated:
    def test_symptom_keywords(self):
        assert is_symptom_related("我头痛") is True
        assert is_symptom_related("最近总是咳嗽") is True
        assert is_symptom_related("发烧怎么办") is True

    def test_no_symptom_keywords(self):
        assert is_symptom_related("藏医的历史") is False
        assert is_symptom_related("你好") is False
