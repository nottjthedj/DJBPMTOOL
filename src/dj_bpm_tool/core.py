import re
import mutagen
from serato_tools.track_tagdump import get_serato_tagdata

# Autotags often contains ASCII like "100.00" inside a small binary blob
_BPM_RE = re.compile(rb'(\d{2,3}\.\d{1,2})')

def extract_bpm_from_mp3(path: str) -> str:
    """
    Returns BPM as a string like '100.00' if found, else ''.
    MP3 only.
    """
    tagfile = mutagen.File(path)
    if tagfile is None:
        return ""

    for desc, payload in get_serato_tagdata(tagfile, decode=False):
        if desc == "Serato Autotags" and isinstance(payload, (bytes, bytearray)):
            m = _BPM_RE.search(payload)
            if m:
                return m.group(1).decode("ascii", "ignore")
    return ""
