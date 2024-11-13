import base64
from functools import cached_property
from pydantic_settings import BaseSettings
from groq import Groq


class Groqqing(BaseSettings):
    """_summary_: Class for groqqing"""

    groq_api_key: str

    @cached_property
    def client(self) -> Groq:
        """_summary_: Create client"""
        return Groq(api_key=self.groq_api_key)

    def groqq(self, content: dict) -> dict:
        """_summary_: Groqq"""
        return self.client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{"role": "user", "content": content}],
            temperature=0.5,
            max_tokens=1000,
            top_p=1.0,
            stream=False,
            stop=None,
        )

    def encode_image(self, file_path: str) -> str:
        """_summary_: Encode image"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def rewrite_caption(self, caption: str) -> str:
        """_summary_: Rewrite caption"""
        content = self.groqq(
            f"Rewrite this description as a one sentence noun phrased image caption. Use only ethical language: {caption}."
        )
        return content.choices[0].message.content

    def tag_image(self, file_path: str) -> str:
        """_summary_: Tag image"""
        content = [
            {
                "type": "text",
                "text": "Create a caption for this image with at most 20 words. .",
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{self.encode_image(file_path)}"
                },
            },
        ]
        return self.groqq(content).choices[0].message.content

    def describe_image(self, file_path: str) -> str:
        """_summary_: Tag image"""
        content = [
            {
                "type": "text",
                "text": "Describe this image as a noun phrase in one sentence.",
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{self.encode_image(file_path)}"
                },
            },
        ]
        return self.groqq(content).choices[0].message.content
