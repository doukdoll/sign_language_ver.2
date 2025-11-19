import os
from typing import Tuple

import cv2
import numpy as np


def draw_text_korean(image: np.ndarray, text: str, position: Tuple[int, int], font_size: int = 28, font_color=(255, 255, 255)) -> np.ndarray:
    """
    OpenCV 기본 폰트는 한글을 지원하지 않으므로, PIL을 사용해 한글 텍스트를 렌더링합니다.
    PIL 미설치 또는 폰트 미발견 시에는 OpenCV로 폴백(한글은 물음표로 보일 수 있음).

    Parameters:
        image: BGR 이미지 배열
        text: 표기할 문자열
        position: 좌상단 기준 위치 (x, y)
        font_size: 글자 크기
        font_color: BGR 색상 튜플

    Returns:
        텍스트가 그려진 BGR 이미지
    """
    if text is None or text == "":
        return image
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        cv2.putText(image, text, (int(position[0]), int(position[1]) + 24), cv2.FONT_HERSHEY_SIMPLEX, 1, font_color, 2, cv2.LINE_AA)
        return image

    candidate_fonts = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/Library/Fonts/AppleGothic.ttf",
        "/Library/Fonts/NanumGothic.ttf",
        "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
    ]
    font = None
    for fp in candidate_fonts:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            cv2.putText(image, text, (int(position[0]), int(position[1]) + 24), cv2.FONT_HERSHEY_SIMPLEX, 1, font_color, 2, cv2.LINE_AA)
            return image

    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    rgb = (int(font_color[2]), int(font_color[1]), int(font_color[0]))
    draw.text((int(position[0]), int(position[1])), text, font=font, fill=rgb)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
