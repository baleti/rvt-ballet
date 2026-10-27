"""Deprecated name: rvt-viewer is now rvt-ballet (package rvtballet). Importing rvtviewer gives rvtballet."""
import sys, warnings
import rvtballet
warnings.warn("rvtviewer is renamed rvtballet", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = rvtballet
