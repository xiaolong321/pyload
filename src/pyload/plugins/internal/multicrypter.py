# -*- coding: utf-8 -*-

from .simplecrypter import SimpleCrypter


class MultiCrypter(SimpleCrypter):
    __name__ = "MultiCrypter"
    __type__ = "hoster"
    __version__ = "0.10"
    __status__ = "stable"

    __pyload_version__ = "0.5"

    __pattern__ = r"^unmatchable$"
    __config__ = [
        ("enabled", "bool", "Activated", True),
        ("use_premium", "bool", "Use premium account if available", True),
        (
            "folder_per_package",
            "Default;Yes;No",
            "Create folder for each package",
            "Default",
        ),
    ]

    __description__ = """Multi decrypter plugin"""
    __license__ = "GPLv3"
    __authors__ = [("Walter Purcaro", "vuolter@gmail.com")]

    def init(self):
        self.PLUGIN_NAME = self.pyload.pluginManager.crypterPlugins.get(self.classname)[
            "name"
        ]

    def _log(self, level, plugintype, pluginname, args, kwargs):
        args = (self.PLUGIN_NAME,) + args
        return SimpleCrypter._log(self, level, plugintype, pluginname, args, kwargs)
