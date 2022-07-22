"""Base component for Lares"""
import logging

import asyncio
import re
import aiohttp
from aiohttp.http import RESPONSES

from lxml import etree

_LOGGER = logging.getLogger(__name__)


class LaresBase:
    """The implementation of the Lares base class."""

    def __init__(self, data: dict):
        username = data["username"]
        password = data["password"]
        host = data["host"]
        port = data["port"]
        if port is None:
            port = "4202"

        self._auth = aiohttp.BasicAuth(username, password)
        self._host = f"http://{host}:{port}"

    async def info(self):
        """Get device info"""
        response = await self.get("info/generalInfo.xml")

        if response is None:
            return None

        info = {
            "name": response.xpath("/generalInfo/productName")[0].text,
            "info": response.xpath("/generalInfo/info1")[0].text,
        }

        return info

    async def zoneDescriptions(self):
        """Get available zones"""
        response = await self.get("zones/zonesDescription48IP.xml")

        if response is None:
            return None

        zones = response.xpath("/zonesDescription/zone")

        return [zone.text for zone in zones]

    async def zones(self):
        """Get available zones"""
        response = await self.get("zones/zonesStatus48IP.xml")

        if response is None:
            return None

        zones = response.xpath("/zonesStatus/zone")

        return [
            {
                "status": zone.find("status").text,
                "bypass": zone.find("bypass").text,
                "alarm": zone.find("alarm").text,
            }
            for zone in zones
        ]

    async def outputDescriptions(self):
        """Get available outputs"""
        response = await self.get("outputs/outputsDescription48IP.xml")

        if response is None:
            return None

        zones = response.xpath("/outputsDescription/output")

        return [zone.text for zone in zones]

    async def outputs(self):
        """Get available zones"""
        response = await self.get("outputs/outputsStatus48IP.xml")

        if response is None:
            return None

        zones = response.xpath("/outputsStatus/output")

        return [
            {
                "status": zone.find("status").text,
                "value": zone.find("value").text,
                "type": zone.find("type").text,
            }
            for zone in zones
        ]

    async def get(self, path):
        """Generic send method."""
        url = f"{self._host}/xml/{path}"

        try:
            async with aiohttp.ClientSession(auth=self._auth) as session:
                async with session.get(url=url) as response:
                    xml = await response.read()
                    content = etree.fromstring(xml)
                    return content

        except aiohttp.ClientConnectorError as conn_err:
            _LOGGER.debug("Host %s: Connection error %s", self._host, str(conn_err))
        except:  # pylint: disable=bare-except
            _LOGGER.debug("Host %s: Unknown exception occurred.", self._host)
        return