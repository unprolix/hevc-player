# Third-Party Notices

HEVC Player distributes and uses third-party software components.
The original HEVC Player source code is licensed under the MIT License
(see `LICENSE`); the components listed below are **not** covered by that
license and remain subject to their respective licenses.

Version information below reflects the components used to build the
v1.0.0 release of `HEVCPlayer.exe`. Rebuilt binaries may contain newer
versions; check the corresponding upstream projects in that case.

## FFmpeg (bundled via PyAV binary wheels)

- Version bundled: libavutil 60.26.102, libavcodec 62.28.102,
  libavformat 62.12.102, libavdevice 62.3.102, libavfilter 11.14.102,
  libswscale 9.5.102, libswresample 6.3.102
- Used for: all media demuxing, decoding (including HEVC/H.265), and
  audio resampling performed by HEVC Player.
- Licensing: FFmpeg is primarily licensed under the GNU Lesser General
  Public License version 2.1 or later (LGPL-2.1+), with optional
  components under other licenses. The PyAV binary wheels used for this
  build include GPL-licensed components (e.g. libx265 is present in the
  wheel). The bundled shared libraries as distributed may therefore be
  subject to GPL terms rather than LGPL; consult the licenses embedded
  in/linked from the libraries themselves.
- Corresponding source: unmodified upstream sources are available at
  https://ffmpeg.org/download.html and https://github.com/PyAV-Org/PyAV/releases
- More information: https://ffmpeg.org/legal.html

## PyAV

- Version: 18.1.0
- Used for: Python bindings to the FFmpeg libraries above.
- License: BSD 3-Clause.
- Source: https://github.com/PyAV-Org/PyAV

## Python

- Version: CPython 3.13
- Used for: application runtime embedded in `HEVCPlayer.exe`.
- License: Python Software Foundation License Version 2 (PSF-2.0).
- Also included: Tcl/Tk toolkit (used for the GUI), under the Tcl/Tk
  license (BSD-style).

## NumPy

- Version: 2.4.6
- Used for: array handling of decoded frames and PCM samples.
- License: BSD 3-Clause.
- Source: https://github.com/numpy/numpy

## Pillow

- Version: 12.3.0
- Used for: color conversion/scaling of video frames for display.
- License: HPND / MIT-CMU (see upstream LICENSE file).
- Source: https://github.com/python-pillow/Pillow

## sounddevice / PortAudio

- sounddevice version: 0.5.6; PortAudio V19.7.0-devel
- Used for: audio playback.
- Licenses: sounddevice — MIT. PortAudio — PortAudio License
  (permissive; see https://www.portaudio.com/license.html).
- Sources: https://github.com/spatialaudio/python-sounddevice ,
  https://github.com/PortAudio/portaudio

## cffi / pycparser

- Versions: cffi 2.1.1, pycparser 3.0
- Used for: native library access by sounddevice.
- Licenses: MIT (cffi), BSD 3-Clause (pycparser).

---

All third-party components above are redistributed unmodified as
published by their respective upstream projects.
