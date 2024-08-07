# A Tool to generate cn font texture and xml files for Taiko Nijiiro Arcade
#
# To execute, run:
#    >>  py cnFont.py "yourFont.ttf" cn
#
# Install Requirements:
#    >>  pip install pillow fonttools
#
# Install NVIDIA Texture Tools from
#    >>  https://developer.nvidia.com/gpu-accelerated-texture-compression
# and set  here
# nvtt_export_path = None
nvtt_export_path = 'C:\\Program Files\\NVIDIA Corporation\\NVIDIA Texture Tools\\nvtt_export.exe'
# current sample is default install path for windows 10

import os, argparse, struct, subprocess, time, math, json
from PIL import Image, ImageFont, ImageDraw, ImageFilter
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont

special = {
    32: lambda real_size: (int(round(0.418 * real_size)), 50),
    160: (13, 50),
    12288: (53, 50),
}

def delete(path):
    # 如果路径是文件，直接删除
    if os.path.isfile(path):
        os.remove(path)
    # 如果路径是文件夹，递归删除所有内容
    elif os.path.isdir(path):
        for file in os.listdir(path):
            delete(os.path.join(path, file))
        os.rmdir(path)  # 删除空文件夹

def findGlyph(font, idx):
    if idx in range(8, 14): return True
    for table in font['cmap'].tables:
        if idx in table.cmap.keys():
            return True
    return False

def clipRect(img, x, y, width, height):
    return img.crop((x, y, x + width, y + height))

def getFontLength(font: ImageFont.FreeTypeFont, char: str):
    return font.getlength(char) if ord(char) > 256 else font.getlength('汉')

def findRect(font: ImageFont.FreeTypeFont, char: str, bbox):
    baseX, baseY, width, height = int(bbox[2] // 2), int(bbox[3] // 2), int(bbox[2] * 2), int(bbox[3] * 2)
    image: Image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw: ImageDraw = ImageDraw.Draw(image)
    draw.text((baseX, baseY), char, font=font, fill='white')

    found = False

    p1x, p1y, p2x, p2y = width, height, 0, 0
    for i, pixel in enumerate(image.getdata()):
        x, y = i % width, i // width
        if pixel[3] != 0:
            found = True
            p1x, p1y, p2x, p2y = min(p1x, x), min(p1y, y), max(p2x, x), max(p2y, y)

    offsetBaseLine = baseY + font.size

    # if found:
    #     print(f'index:{ord(char)}')
    #     print(f'baseX:{baseX} baseY:{baseY}')
    #     print(f'p1:{p1x},{p1y} p2:{p2x},{p2y}')
    #     print(f'baselineY:{offsetBaseLine}')

    drawOffsetX, drawOffsetY = baseX - p1x, baseY - p1y
    uponBaseLine, downBaseLine = offsetBaseLine - p1y, p2y - offsetBaseLine

    # if found:
    #     print(f'drawOffX:{drawOffsetX} drawOffY:{drawOffsetY}')
    #     print(f'baseline:{uponBaseLine},{downBaseLine}')
    #     time.sleep(2)

    if found: return (True, (p1x - baseX, p1y - baseY, p2x - baseX + 1, p2y - baseY + 1), (drawOffsetX, drawOffsetY), (uponBaseLine, downBaseLine))
    return (False, (0, 0, 1, 1), (0, 0), (0, 0))

def fixLine(glyphList: list, lineGlyph: list, minUponBaseLineAddition: int):
    if minUponBaseLineAddition <= 0: return
    print(f"cut top {minUponBaseLineAddition}")
    for idx in lineGlyph:
        glyphList[idx]['y'] = glyphList[idx]['y'] - minUponBaseLineAddition
        glyphList[idx]['glyph']['height'] = glyphList[idx]['glyph']['height'] - minUponBaseLineAddition

def getPadVertical(glyphInfoList: list, char: str, maxBaseline: tuple, pixel: int, size: int):
    for i, _, rect, _, base in  glyphInfoList:
        if i == ord(char):
            uponBaseLineAddition = maxBaseline[0] - base[0]
            padT = pixel - uponBaseLineAddition
            padB = size - maxBaseline[0] - maxBaseline[1] - padT
            # print(uponBaseLineAddition, size, rect, padT, padB)
            # time.sleep(100)
            return (padT, padB)
    raise f'字体中不存在"{char}"字'

def alignHeight(imageHeight: int, type: int) -> int:
    if type == 0: return imageHeight
    elif type == 1: return imageHeight // 4 * 4 + (4 if imageHeight % 4 > 1 else 0)
    elif type == 2: return pow(2, math.ceil(math.log2(imageHeight)))

# def calcPaddings(font: ImageFont.FreeTypeFont, char: str, w: int, h: int, padL: int, padT: int):
#     image: Image = Image.new("RGBA", (w * 2, h * 2), (255, 255, 255, 0))
#     draw: ImageDraw = ImageDraw.Draw(image)
#     bbox = draw.textbbox((0, 0), char, font=font)
#     rect = findRect(font, char, bbox)
#     padR = w - padL - (rect[2] - rect[0])
#     padB = h - padT - (rect[3] - rect[1])
#     return (padL, padT, padR, padB)

def calcFontInfos(ttf_path: str, font_type: int, example: tuple = ('演', 4, 64), spacing: tuple = (0, 0), limit = range(0, 65535)) -> dict:
    maxWidth: int = 4096

    image: Image = Image.new("RGBA", (maxWidth, 4096), (255, 255, 255, 0))
    draw: ImageDraw = ImageDraw.Draw(image)

    glyphList: list = []
    
    # offsetX, offsetY = offset
    # if offsetX < 0: padL, padR = 0, 2 * -offsetX
    # else: padL, padR = 2 * offsetX, 0
    # if offsetY < 0: padT, padB = 0, 2 * -offsetY
    # else: padT, padB = 2 * offsetY, 0
    padL, padR = 1, 2
    spaceX, spaceY = spacing

    if font_type == 30:
        real_size = 30
        font: ImageFont.FreeTypeFont = ImageFont.truetype(ttf_path, real_size)
        # padL, padT, padR, padB = calcPaddings(font, chr(39181), 30, 35, 0, 2)
        font_size, font_point, half_size = 53, 30, 15
    elif font_type == 64:
        real_size = 56
        font: ImageFont.FreeTypeFont = ImageFont.truetype(ttf_path, real_size)
        # padL, padT, padR, padB = calcPaddings(font, chr(39181), 56, 64, 0, 2)
        font_size, font_point, half_size = 72, 56, 32

    ttFont = TTFont(ttf_path)
    
    glyphInfoList = []
    maxUponBaseLineChar, maxDownBaseLineChar = '', ''
    maxUponBaseLine, maxDownBaseLine = 0, 0
    print(f'Start calc rect & baseline...')
    for i in limit:
        if i not in range(0, 65535): continue
        found: bool = findGlyph(ttFont, i) or i in special
        if not found: continue

        # print(i)

        bbox = draw.textbbox((0, 0), chr(i), font=font)
        exist, rect, drawOffset, base = findRect(font, chr(i), bbox)
        if exist:
            maxUponBaseLine = max(maxUponBaseLine, base[0])
            if maxUponBaseLine == base[0]: maxUponBaseLineChar = chr(i)
            maxDownBaseLine = max(maxDownBaseLine, base[1])
            if maxDownBaseLine == base[1]: maxDownBaseLineChar = chr(i)

        # time.sleep(2)

        glyphInfoList.append((i, exist, rect, drawOffset, base))

    print(f'calc rect & baseline Finished! {maxUponBaseLineChar}[{ord(maxUponBaseLineChar)}]({maxUponBaseLine}), {maxDownBaseLineChar}[{ord(maxDownBaseLineChar)}]({maxDownBaseLine})')

    padT, padB = getPadVertical(glyphInfoList, example[0], (maxUponBaseLine, maxDownBaseLine), example[1], example[2])
    
    baseX, baseY = 0, 0
    
    currentMaxHeight: int = 0
    lineList, minUponBaseLineAddition = [], 4096
    for i, exist, rect, drawOffset, base in glyphInfoList:
        # print(i, rect, drawOffset, base)
        uponBaseLineAddition = maxUponBaseLine - base[0]
        minUponBaseLineAddition = min(minUponBaseLineAddition, uponBaseLineAddition)

        if i in special:
            if isinstance(special[i] ,tuple):
                width, height = special[i]
            else: width, height = special[i](real_size)
        elif exist:
            width, height = rect[2] - rect[0] + padL + padR, maxUponBaseLine + maxDownBaseLine + padT + padB
        else: width, height = 4, 1

        if baseX + width > maxWidth:
            # if baseY == 0: baseY += int(round(real_size / 15))
            baseY = baseY + currentMaxHeight + spaceY
            baseX, currentMaxHeight = 0, 0
            # fixLine(glyphList, lineList, minUponBaseLineAddition)
            lineList, minUponBaseLineAddition = [], 4096

        # if exist:
        drawX, drawY = baseX + drawOffset[0] + padL, baseY + drawOffset[1] + padT + uponBaseLineAddition
        # drawX, drawY = baseX + drawOffset[0], baseY + drawOffset[1]
        # else: drawX, drawY = baseX + padL, baseY + padL
        
        # print(i, drawX, drawY, baseX, baseY, drawOffset, base, padL, padT, uponBaseLineAddition)

        meta = {"glyph": {'index': i, 'type': 1, 'offsetU': baseX, 'offsetV': baseY, 'width': width, 'height': height}, "x": drawX, "y": drawY}
        lineList.append(len(glyphList))
        glyphList.append(meta)
        # print(meta)

        # time.sleep(2)

        baseX = baseX + width + spaceX
        currentMaxHeight = max(currentMaxHeight, height)

    # fixLine(glyphList, lineList, minUponBaseLineAddition)
    imageHeight = baseY + currentMaxHeight
    tex_height = alignHeight(imageHeight, type=1)

    return {'texWidth': 4096, 'texHeight': tex_height, 'fontSize': font_size, 'fontPoint': font_point, 'realSize': real_size, 'fixedHalfWidth': half_size, 'glyphList': glyphList}

def drawFontImage(ttf_path: str, fontInfos: dict) -> Image:
    image = Image.new("RGBA", (fontInfos['texWidth'], fontInfos['texHeight']), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(ttf_path, fontInfos['realSize'])

    for glyphMeta in fontInfos['glyphList']:
        print(glyphMeta)
        char = chr(glyphMeta['glyph']['index'])
        drawX = glyphMeta['x']
        drawY = glyphMeta['y']

        # length = getFontLength(font, char)

        draw.text((drawX, drawY), char, font=font, fill="white")
        # draw.line((drawX, drawY + length, drawX + glyphMeta['glyph']['width'], drawY + length), fill='black')

    image.filter(ImageFilter.SMOOTH_MORE)

    return image

fontSizeMap = {30: 53, 32: 53, 64: 72}

def writeFontXml(fontInfos: dict) -> ET.Element:
    root_element = ET.Element("root")
    font_element = ET.SubElement(
        root_element, "font", 
        texWidth=str(fontInfos['texWidth']), 
        texHeight=str(fontInfos['texHeight']), 
        fontSize=str(fontInfos['fontSize']), 
        fontPoint=str(fontInfos['fontPoint']), 
        fixedHalfWidth=str(fontInfos['fixedHalfWidth']), 
        glyphNum=str(max(0, len(fontInfos['glyphList']) - 1))
    )

    for glyphMeta in fontInfos['glyphList']:
        glyph = glyphMeta['glyph']
        ET.SubElement(
            font_element, "glyph", 
            index=str(glyph['index']), 
            type=str(glyph['type']), 
            offsetU=str(glyph['offsetU']), 
            offsetV=str(glyph['offsetV']), 
            width=str(glyph['width']), 
            height=str(glyph['height']),
            # drawX=str(glyphMeta['x']),
            # drawY=str(glyphMeta['y'])
        )
    
    return root_element

def getConverter(): 
    if os.path.exists('./texconv.exe'): 
        def converter(pngPath: str, ddsPath: str):
            print('converting png to dds using texconv.exe...')
            subprocess.run(f'"./texconv.exe" -f BC7_UNORM -y -if LINEAR "{pngPath}"')
    elif os.path.exists('./nvtt_export.exe'):
        def converter(pngPath: str, ddsPath: str):
            print('converting png to dds using nvtt_export.exe...')
            subprocess.run(f'"./nvtt_export.exe" "{pngPath}" --format bc7 --output {ddsPath}')
    elif os.path.exists(nvtt_export_path):
        def converter(pngPath: str, ddsPath: str):
            print('converting png to dds using NVDIA Texture Tools...')
            subprocess.run(f'"{nvtt_export_path}" "{pngPath}" --format bc7 --output {ddsPath}')
    else: converter = None
    return converter

dataA = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x34\x36\x58\x54'
dataB = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00'
dataC = b'\x00\x00\x01\x00\x00\x00\xE0\x04\x00\x00\x04\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00'
dataD = b'\x20\x58\x45\x54\x01\x00\x02\x00'
def convertPngToNutexb(pngPath: str, ddsPath: str, nutPath: str, gen_mark: str, imageHeight: int) -> bool:
    converter = getConverter()
    if converter == None: return False
    else: converter(pngPath, ddsPath)
    with open(ddsPath, 'rb') as source, open(nutPath, 'wb') as target:
        # 跳过前0x94个字节
        source.seek(0x94)
        # 读取剩余的所有数据并写入目标文件
        target.write(source.read())
        sizeData = struct.pack('I', int('1000000', 16) * math.ceil(imageHeight / 4096))
        target.write(sizeData)
        target.write(dataA)
        target.write(gen_mark.encode('ascii'))
        target.write(dataB)
        target.write(struct.pack('H', imageHeight))
        target.write(dataC)
        target.write(sizeData)
        target.write(dataD)
    return True

def fontProcessing(ttf_path: str, font_base: str, font_point: 30, example=('演', 4, 64), spacing=(3, 4), limit=range(0, 65535)) -> None:
    gen_mark = f'{font_base}_{font_point}'
    output_png_path = f'out/{gen_mark}.png'
    output_xml_path = f'out/{gen_mark}.xml'
    output_dds_path = f'out/{gen_mark}.dds'
    output_nut_path = f'out/{gen_mark}.nutexb'

    fontInfos: dict = calcFontInfos(ttf_path, font_point, example, spacing, limit)
    pngImage: Image = drawFontImage(ttf_path, fontInfos)
    root_element: ET.Element = writeFontXml(fontInfos)

    pngImage.save(output_png_path)
    element_tree = ET.ElementTree(root_element)
    element_tree.write(output_xml_path, encoding="utf-8", xml_declaration=True)

    converted: bool = convertPngToNutexb(output_png_path, output_dds_path, output_nut_path, gen_mark, fontInfos['texHeight'])

    # Format the XML file to match the provided structure
    import xml.dom.minidom
    xml_str = xml.dom.minidom.parseString(ET.tostring(root_element)).toprettyxml(indent="  ")
    with open(output_xml_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(xml_str.replace('<?xml version="1.0" ?>', '').strip())

    # cleanup
    # if os.path.exists(output_png_path): os.remove(output_png_path)
    # if os.path.exists(output_dds_path): os.remove(output_dds_path)
    if not converted:
        print(f'''
    !!! This Program Support generate nutexb file automatically !!!

    Nvdia Texture Tools are not found either in 
        - Its default install path
        - Same path of this program
    
    Maybe you haven't install it yet, Here is the Official Site: 
              
        https://developer.nvidia.com/gpu-accelerated-texture-compression
              
    Install it and retry generation, nutexb will automatically generate for you!
              
    If you're not interested in this feature, you can manually close the window.
    Execution is Finished.
''')
        time.sleep(24 * 60 * 60)

ttf_path = "FZPW-STJ.ttf"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert TTF font to texture and XML')
    parser.add_argument('ttf_path', type=str, help='Path to the TTF font file')
    parser.add_argument('-n', '--name', type=str, help='Base Name in front of the file, default: cn', default='cn')
    parser.add_argument('--c30', type=str, help='Test Top Offset Char of xx_30, default: 演', default='演')
    parser.add_argument('--t30', type=int, help='Top Offset of xx_30, default: 2', default=2)
    parser.add_argument('--h30', type=int, help='Standard height of xx_30, default: 35', default=35)
    parser.add_argument('--c64', type=str, help='Test Top Offset Char of xx_64, default: 演', default='演')
    parser.add_argument('--t64', type=int, help='Top Offset of xx_64, default: 4', default=4)
    parser.add_argument('--h64', type=int, help='Standard height of xx_64, default: 64', default=64)
    parser.add_argument('--limit', type=str, help='Limit generation list json', required=False)
    args = parser.parse_args()

    if not os.path.exists('out'): os.makedirs('out')
    limit = range(0, 65535)
    if args.limit:
        with open(args.limit, 'r') as f: limit = json.load(f)

    fontProcessing(args.ttf_path, args.name, 30, example=(args.c30, args.t30, args.h30), limit=limit)
    fontProcessing(args.ttf_path, args.name, 64, example=(args.c64, args.t64, args.h64), limit=limit)
