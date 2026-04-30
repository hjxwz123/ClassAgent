from collections.abc import Sequence


class MockAIService:
    def generate_page_script(self, *, title: str | None, content: str) -> str:
        heading = title or "本页内容"
        summary = content.strip().replace("\n", " ")
        summary = summary[:220] if len(summary) > 220 else summary
        return (
            f"{heading}的核心内容如下：\n"
            f"1. 先理解本页定义与背景：{summary or '本页暂无可提取文字。'}\n"
            f"2. 再关注概念之间的联系与典型应用。\n"
            f"3. 最后结合课程上下文总结本页重点并准备继续学习。"
        )

    def summarize_lesson(self, title: str, page_texts: Sequence[str]) -> str:
        merged = " ".join(text.strip() for text in page_texts if text.strip())
        merged = merged[:200] if len(merged) > 200 else merged
        return f"{title}：{merged or '该资料已生成课堂页面，可继续补充讲解脚本。'}"


ai_service = MockAIService()
