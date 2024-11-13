import os
from random import choice
import time
from functools import cached_property
import requests
from requests import Response
from pydantic_settings import BaseSettings
from imagegen.lib.schema import ImagePrompt

waits = range(30, 240, 5)


class MidjourneyClient(BaseSettings):
    """_summary_: Class for midjourney"""

    discord_api_url: str
    discord_application_id: str
    discord_data_version: str
    discord_data_id: str
    discord_channel_id: str
    discord_user_token: str
    discord_session_id: str
    discord_guild_id: str
    user_agent: str
    model: str = "midjourney"

    def _get_response(self, url: str) -> dict:
        """_summary_: Get response"""
        return self.client.get(url, verify=False, headers={""}).json()

    def _post_response(self, url: str, data: dict) -> Response:
        """_summary_: Post response"""
        return self.client.post(url, json=data, verify=False)

    @cached_property
    def headers(self) -> dict:
        """_summary_: Create headers"""
        return {"Authorization": self.discord_user_token, "User-Agent": self.user_agent}

    @cached_property
    def client(self) -> requests.Session:
        """_summary_: Create client"""
        client = requests.Session()
        client.headers.update(self.headers)
        return client

    @cached_property
    def discord_user_id(self) -> str:
        """_summary_: Create user id"""
        response = self._get_response(f"{self.discord_api_url}/users/@me")
        return response["id"]

    def _upscale_image(self, message_id: str, component_id: str):
        """_summary_: Upscale image"""
        params = {
            "type": 3,
            "guild_id": self.discord_guild_id,
            "channel_id": self.discord_channel_id,
            "message_id": message_id,
            "application_id": self.discord_application_id,
            "session_id": self.discord_session_id,
            "data": {
                "component_type": 2,
                "custom_id": component_id,
            },
        }

        self._post_response(f"{self.discord_api_url}/interactions", data=params)
        time.sleep(choice(waits))

    def search_messages(self, prompt: str, query: str) -> dict:
        """_summary_: Search messages"""

        def _func():
            return next(
                filter(
                    lambda x: prompt.lower() in x.get("content").lower()
                    and query.lower() in x.get("content").lower()
                    and len(x.get("attachments")) > 0
                    and len(x.get("components")) > 0,
                    self.get_messages(),
                ),
                None,
            )

        count = 0
        while not (message := _func()):
            if count > 10:
                return None
            print("Image not generated, waiting 10 seconds")
            time.sleep(choice(waits))
            count += 1
        return message

    def get_messages(self) -> dict:
        """_summary_: Get imagine"""
        return self.client.get(
            f"{self.discord_api_url}/channels/{self.discord_channel_id}/messages",
            verify=False,
        ).json()

    def get_message(self, message_id: str) -> dict:
        """_summary_: Get message"""
        return self.client.get(
            f"{self.discord_api_url}/channels/{self.discord_channel_id}/messages/{message_id}",
            verify=False,
        ).json()

    def delete_message(self, message_id: str):
        """_summary_: Delete a message from the current channel"""
        self.client.delete(
            f"{self.discord_api_url}/channels/{self.discord_channel_id}/messages/{message_id}",
            verify=False,
        )

    def delete_messages(self):
        """_summary_: Delete all messages in the current channel"""
        while len(self.get_messages()) > 0:
            message_ids = [message["id"] for message in self.get_messages()]
            for message_id in message_ids:
                self.delete_message(message_id)
                time.sleep(2)
        time.sleep(choice(waits))
        assert len(self.get_messages()) == 0

    def get_attachments(self, message_id: dict) -> dict:
        """_summary_: Get the generated image from the message"""
        return self.client.post(
            f"{self.discord_api_url}/channels/{self.discord_channel_id}/messages/{message_id}/attachments",
            verify=False,
        ).json()

    def get_components(self, message: dict) -> list[str]:
        """_summary_: Get components"""
        components = [
            [c.get("custom_id", None) for c in component["components"]]
            for component in message["components"]
        ]
        return [
            item
            for sublist in components
            for item in sublist
            if item and "upsample" in item
        ]

    def imagine(self, prompt: ImagePrompt):
        """_summary_: Imagine"""
        # self.delete_messages()
        params = {
            "type": 2,
            "application_id": self.discord_application_id,
            "guild_id": self.discord_guild_id,
            "channel_id": self.discord_channel_id,
            "session_id": self.discord_session_id,
            "data": {
                "version": self.discord_data_version,
                "id": self.discord_data_id,
                "name": "imagine",
                "type": 1,
                "options": [
                    {
                        "type": 3,
                        "name": "prompt",
                        "value": f"{prompt.prompt} shot on a Sony A7III, UHD ultra-realistic hyper-detail, high detailing, highly detailed realism, crisp --v 6.1 --c 25 --ar 111:111 --style raw --stylize 750 --q 2",
                    }
                ],
                "application_command": {
                    "id": self.discord_data_id,
                    "application_id": self.discord_application_id,
                    "version": self.discord_data_version,
                    "default_member_permissions": None,
                    "type": 1,
                    "nsfw": False,
                    "name": "imagine",
                    "description": "Create images with Midjourney",
                    "dm_permission": True,
                    "options": [
                        {
                            "type": 3,
                            "name": "prompt",
                            "description": "The prompt to imagine",
                            "required": True,
                        }
                    ],
                },
                "attachments": [],
            },
        }
        self._post_response(f"{self.discord_api_url}/interactions", data=params)
        print("Prompt sent to Discord......................\n")
        time.sleep(180)

    def upscale_images(self, prompt: str, message: dict):
        """_summary_: Upscale images"""
        _messages = []
        if comps := self.get_components(message):
            for index, comp in enumerate(comps):
                self._upscale_image(message_id=message.get("id"), component_id=comp)
                _messages.append(
                    self.search_messages(prompt=prompt, query=f"image #{index+1}")
                )
                time.sleep(choice(waits))
        return _messages


class Midjourney:
    """_summary_: Class for midjourney"""

    def __init__(
        self, prompt: ImagePrompt, client: MidjourneyClient, model: str = "midjourney"
    ):
        self.prompt = prompt
        self.client = client
        self.model = model

    @cached_property
    def output_dir(self) -> str:
        """_summary_: Create output dir"""
        return f"imagegen/images/output/generated/{self.model}/raw"

    def _save_image(self, message: dict, tag: str | None = ""):
        tag = f"{self.prompt.id}_{tag}" if tag else self.prompt.id
        with open(f"{self.output_dir}/{tag}.{self.prompt.output_format}", "wb") as f:
            f.write(
                requests.get(
                    message["attachments"][0]["url"],
                    headers={"user-agent": "Mozilla"},
                    timeout=10,
                    verify=False,
                ).content
            )
        f.close()
        assert os.path.exists(f"{self.output_dir}/{tag}.{self.prompt.output_format}")

    def save_captions(self, messages: list[dict]):
        """_summary_: Save caption"""
        with open("captions.csv", "a", encoding="utf-8") as f:
            for message in messages:
                f.write(
                    f"{self.prompt.id},{message.get('id')},{self.prompt.prompt.replace(',', '')},{self.prompt.raw.replace(',', '')},{self.prompt.url},{message.get('attachments')[0]['url']}\n"
                )
        f.close()

    def generate(self):
        """_summary_: Imagine"""
        print(
            f"Clearing Current Messages in channel {self.client.discord_channel_id}\n\n\n\n"
        )
        self.client.delete_messages()
        print("Sending Prompt to Discord ....................\n\n\n")

        print("Generating Image....................\n\n\n")
        self.client.imagine(prompt=self.prompt)

        print("Waiting for Image to be generated....................\n\n\n")
        message = self.client.search_messages(prompt=self.prompt.prompt, query="(fast)")

        print("Generated Image....................\n\n\n")
        print(message)

        print("Upscaling and Saving Image Variants....................\n\n\n")
        variants = self.client.upscale_images(
            prompt=self.prompt.prompt, message=message
        )
        saved = [
            self._save_image(message=variant, tag=f"_{index+1}")
            for index, variant in enumerate(variants)
        ]
        self.save_captions(messages=variants)
        assert all(saved)

    '''def upload_image(self):
        """_summary_: Upload image"""
        file_path = f"{self.prompt.input_dir}/{self.prompt.id}.{self.prompt.output_format}"
        with open(file_path, "rb") as f:
            res = self._post_response(
                f"{self.discord_api_url}/channels/{self.discord_channel_id}/attachments",
                data={
                    "files": [{
                            "id": 0,
                            "filename": file_path,
                            "file_size": f.__sizeof__()
                        }]
                }
            )
            print(res.json())
            _url = res.json()["attachments"][0]["upload_url"]
        self.prompt.prompt = f"https://cdn.discordapp.com/attachments/{self.discord_channel_id}/{self.prompt_message['id']}/{_url.split("/")[-1]}   {self.prompt.prompt}"
        self.output_dir = "imagegen/images/output/generated/midjourney/finetuned"
        self.imagine_prompt()
        time.sleep(5)

        print("Upscaling and Saving Images")
        return self.upscale()'''
