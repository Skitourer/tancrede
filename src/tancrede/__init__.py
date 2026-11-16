"""Tancrède: a desktop assistant for notes, projects and cognitive load."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tancrede")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0+unknown"
