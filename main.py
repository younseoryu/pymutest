import fitz
from multi_column import column_boxes

doc = fitz.open("sample6.pdf")
for page in doc:
    # print("page.number", page.number)
    bboxes = column_boxes(page, footer_margin=0, header_margin=0, no_image_text=False)
    for rect in bboxes:
        print(page.get_text(clip=rect, sort=True))
    print("-" * 80)

# page_text = ""
# for page_number, page in enumerate(doc):
#         page_text =  page_text + page.get_text()
# print(page_text)
    