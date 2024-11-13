from functools import cached_property
from typing import Literal
from pydantic import BaseModel
from imagegen.lib.groqqing import Groqqing


class ImagePrompt(BaseModel):
    """_summary_: Class for image prompt"""

    id: str
    raw: str
    url: str
    prompt: str
    sample_size: int = 2
    height: int = 2000
    width: int = 2000
    image_name: str
    labels: list[str]
    input_path: str
    input_dir: str = "imagegen/images/inputs/annotated"
    output_format: Literal["png", "jpeg", "jpg"] = "png"

    @cached_property
    def groqqed(self) -> str:
        """_summary_: Groqqed"""
        return Groqqing().tag_image(self.input_path)
