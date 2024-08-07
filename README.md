# TaikoFont
TaikoFont Generator

```
$ v2cnFont.exe --help
usage: v2cnFont.py [-h] [-n NAME] [--c30 C30] [--t30 T30] [--h30 H30] [--c64 C64] [--t64 T64] [--h64 H64] [--limit LIMIT] ttf_path

Convert TTF font to texture and XML

positional arguments:
  ttf_path              Path to the TTF font file

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Base Name in front of the file, default: cn
  --c30 C30             Test Top Offset Char of xx_30, default: 演
  --t30 T30             Top Offset of xx_30, default: 2
  --h30 H30             Standard height of xx_30, default: 35
  --c64 C64             Test Top Offset Char of xx_64, default: 演
  --t64 T64             Top Offset of xx_64, default: 4
  --h64 H64             Standard height of xx_64, default: 64
  --limit LIMIT         Limit generation list json
```