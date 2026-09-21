"""Process-local Cairo loading; no global PATH or machine configuration changes."""
import os
import io
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

_handles = []
_converter = None


def converter():
    global _converter
    if _converter is None:
        directory = Path(sys.prefix) / 'Library' / 'bin'
        if os.name == 'nt' and directory.is_dir():
            _handles.append(os.add_dll_directory(str(directory)))
            os.environ['CAIROCFFI_DLL_DIRECTORIES'] = str(directory)
        import cairosvg
        _converter = cairosvg
    return _converter


def svg_to_png(svg_bytes, width, height):
    """Preserve embedded artwork notices when exporting a licensed SVG as PNG."""
    png = converter().svg2png(bytestring=svg_bytes, output_width=width, output_height=height)
    notices = [node.text for node in ET.fromstring(svg_bytes).iter()
               if node.tag.rsplit('}', 1)[-1] == 'desc' and node.text]
    if not notices:
        return png
    from PIL import Image, PngImagePlugin
    metadata = PngImagePlugin.PngInfo()
    metadata.add_itxt('Description', '\n\n'.join(notices))
    output = io.BytesIO()
    with Image.open(io.BytesIO(png)) as picture:
        picture.save(output, format='PNG', pnginfo=metadata)
    return output.getvalue()
