import fitz
from multi_column import column_boxes

doc = fitz.open("sample3.pdf")
for page in doc:
    bboxes = column_boxes(page, footer_margin=50, no_image_text=True)
    for rect in bboxes:
        print(page.get_text(clip=rect, sort=True))
    print("-" * 80)