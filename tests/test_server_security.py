import unittest

from server import is_public_asset


class StaticAssetSecurityTests(unittest.TestCase):
    def test_ui_assets_are_public(self):
        self.assertTrue(is_public_asset("/"))
        self.assertTrue(is_public_asset("/app.js"))
        self.assertTrue(is_public_asset("/assets/fontawesome/css/all.min.css"))

    def test_runtime_configuration_and_source_are_private(self):
        self.assertFalse(is_public_asset("/install.env"))
        self.assertFalse(is_public_asset("/.git/config"))
        self.assertFalse(is_public_asset("/server.py"))
        self.assertFalse(is_public_asset("/polysocial/vault.py"))


if __name__ == "__main__":
    unittest.main()
