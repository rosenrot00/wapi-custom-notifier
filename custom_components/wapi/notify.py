import logging

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant.components.notify import (
    ATTR_TARGET,
    ATTR_TITLE,
    ATTR_DATA,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)

CONF_URL = "url"
CONFIG_SESSION = "session"
CONFIG_TOKEN = "token"
_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_URL): cv.string,
        vol.Required(CONFIG_SESSION): cv.string,
        vol.Optional(CONFIG_TOKEN): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

def get_service(hass, config, discovery_info=None):
    """Get the custom notifier service."""
    url = config.get(CONF_URL)
    session = config.get(CONFIG_SESSION)
    token = config.get(CONFIG_TOKEN)
    return MatterNotificationService(url, session, token)

class MatterNotificationService(BaseNotificationService):
    def __init__(self, url, session, token=None):
        self._url = url
        self.session = session
        self.token = token

    def __send(self, data):
        try:
            if self.token is None:
                response = requests.post(self._url + "/" + self.session, json=data)
            else:
                headers = {"x-api-key": self.token}
                response = requests.post(
                    self._url + "/" + self.session, json=data, headers=headers
                )
            _LOGGER.info("Message sent")
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            _LOGGER.error("Error sending notification using wapi: %s", ex)

    def send_message(self, message="", **kwargs):
        title = kwargs.get(ATTR_TITLE) or ""
        chatId = kwargs.get(ATTR_TARGET)
        data = kwargs.get(ATTR_DATA) or {}
        media_urls = data.get("media_url", "").splitlines() if data.get("media_url") else []
        message = "" if message == " " else message
        ascaption = data.get("ascaption", False)

        def format_text(title, message):
            return ("*" + title + "*" + ("\n" if message else "") if title else "") + (message or "")

        if ascaption and len(media_urls) > 1:
            _LOGGER.warning("Multiple media URLs provided, but 'ascaption' is true. Only the first URL will have a caption.")

        if not media_urls:
            self.__send({
                "content": format_text(title, message),
                "chatId": chatId,
                "contentType": "string",
            })
            return

        if ascaption:
            self.__send({
                "chatId": chatId,
                "contentType": "MessageMediaFromURL",
                "content": media_urls[0],
                "options": {"caption": format_caption(title, message)}
            })
            media_urls = media_urls[1:]
        elif title or message:
            self.__send({
                "content": format_text(title, message),
                "chatId": chatId,
                "contentType": "string",
            })

        for url in media_urls:
            self.__send({
                "chatId": chatId,
                "contentType": "MessageMediaFromURL",
                "content": url,
            })
