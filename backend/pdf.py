import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from PIL import Image


def images_to_pdf(image_dir, output_pdf):
    # A4 尺寸
    page_width, page_height = A4

    # 卡片尺寸固定 4x6 cm
    card_width = 4 * cm
    card_height = 6 * cm

    # 每页排布（横向几列、纵向几行）
    cols = int(page_width // card_width)
    rows = int(page_height // card_height)

    c = canvas.Canvas(output_pdf, pagesize=A4)

    x_margin = (page_width - cols * card_width) / 2
    y_margin = (page_height - rows * card_height) / 2

    x, y = x_margin, page_height - y_margin - card_height

    # 文本样式
    style1 = ParagraphStyle(
        name="CardText1",
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.red,
        alignment=TA_CENTER,
        leading=22,
    )
    style2 = ParagraphStyle(
        name="CardText2",
        fontName="Helvetica",
        fontSize=12,
        textColor=colors.black,
        alignment=TA_CENTER,
        leading=14,
    )

    for fname in sorted(os.listdir(image_dir)):
        if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        img_path = os.path.join(image_dir, fname)

        # 画边框
        c.setStrokeColor(colors.lightgrey)
        c.rect(x, y, card_width, card_height)

        # 图片区域：4x4 cm
        img_box_w = 4 * cm
        img_box_h = 4 * cm
        img_box_x = x
        img_box_y = y + (card_height - img_box_h)

        # 保持比例缩放
        with Image.open(img_path) as img:
            iw, ih = img.size
            aspect = iw / ih
            if img_box_w / img_box_h > aspect:
                draw_height = img_box_h
                draw_width = draw_height * aspect
            else:
                draw_width = img_box_w
                draw_height = draw_width / aspect

        # 居中放置
        img_x = img_box_x + (img_box_w - draw_width) / 2
        img_y = img_box_y + (img_box_h - draw_height) / 2
        c.drawImage(ImageReader(img_path), img_x, img_y,
                    draw_width, draw_height, preserveAspectRatio=True, mask='auto')

        # 文本区域：下方 2 cm
        text_box_h = 2 * cm
        text_box_y = y
        filename = os.path.splitext(fname)[0]

        # 按第一个下划线分割
        if " " in filename:
            part1, part2 = filename.split(" ", 1)
        else:
            part1, part2 = filename, ""

        # 第一部分 → 上半区（红色 20）
        para1 = Paragraph(part1, style1)
        w1, h1 = para1.wrap(card_width - 6, text_box_h / 2)
        para1.drawOn(
            c,
            x + (card_width - w1) / 2,
            text_box_y + text_box_h / 2 + (text_box_h / 2 - h1) / 2
        )

        # 第二部分 → 下半区（黑色 12）
        if part2:
            para2 = Paragraph(part2, style2)
            w2, h2 = para2.wrap(card_width - 6, text_box_h / 2)
            para2.drawOn(
                c,
                x + (card_width - w2) / 2,
                text_box_y + (text_box_h / 2 - h2) / 2
            )

        # 下一个卡片
        x += card_width
        if x + card_width > page_width - x_margin + 1:
            x = x_margin
            y -= card_height
            if y < y_margin - card_height:
                c.showPage()
                x, y = x_margin, page_height - y_margin - card_height

    c.save()


if __name__ == "__main__":
    image_dir = "/Users/luoqi/APP/png"
    output_pdf = "plu.pdf"
    images_to_pdf(image_dir, output_pdf)
    print(f"PDF 生成完成: {output_pdf}")
