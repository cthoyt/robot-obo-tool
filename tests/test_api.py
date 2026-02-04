"""Trivial version test."""

import tempfile
import unittest
from pathlib import Path

from robot_obo_tool.api import ROBOTError, convert, get_robot_jar_path, is_available
from robot_obo_tool.version import get_version


class TestVersion(unittest.TestCase):
    """Trivially test a version."""

    def test_version_type(self) -> None:
        """Test the version is a string.

        This is only meant to be an example test.
        """
        version = get_version()
        self.assertIsInstance(version, str)

    def test_get_path(self) -> None:
        """Test getting the JAR path."""
        self.assertIsNotNone(get_robot_jar_path())

    def test_robot_is_available(self) -> None:
        """Test ROBOT is available."""
        self.assertTrue(is_available())

    def test_parse_owl(self) -> None:
        """Test parsing a remote JSON graph, should take less than a minute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir).joinpath("pato.obo")
            uri = "https://raw.githubusercontent.com/pato-ontology/pato/master/pato.owl"
            with self.assertRaises(ROBOTError):
                convert(uri, path, check=True)
            convert(uri, path, check=False)
            self.assertIn(
                'property_value: dc:title "PATO - the Phenotype And Trait Ontology" xsd:string',
                path.read_text(),
            )
