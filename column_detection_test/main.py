import fitz
from multi_column import is_the_double_column_resume
from kmeans import kmeans_1d
import os

def is_double_column_resume(bboxes, x0_values):
    # extract x0 of each bbox to form the dataset for K-means
    x0_values = [bbox.x0 for bbox in bboxes]
    # handle case with less than 2 bboxes, assuming single-column layout
    if len(x0_values) < 2:
        return bboxes  # or handle as a special case as needed
    # apply K-means clustering on x0 values
    centroids, _ = kmeans_1d(x0_values, k=2)
    # determine if it's single or double-column based on centroids difference
    # it's double column if centroids diff is larger than 1/4 of page width
    if abs(centroids[0] - centroids[1]) > page.rect.width / 4:
        return True
    else:
        return False


print('------------------------------------------------------------')
print('below are single column resumes')
print('------------------------------------------------------------')
directory = "single_column_resumes"
for filename in os.listdir(directory):
    file_path = os.path.join(directory, filename)
    if os.path.isfile(file_path) and filename != ".DS_Store":
        doc = fitz.open(file_path)
        formatted_filename = f"{filename:<50.50}"  
        print(f"{formatted_filename} ->", end=" ")
        for i, page in enumerate(doc, start=1):
            column_type = "double" if is_the_double_column_resume(page, footer_margin=0, header_margin=0, no_image_text=False) else "single"
            if i < len(doc):
                print(f"page{i}: {column_type} ||", end=" ")
            else:
                print(f"page{i}: {column_type}") 

print('\n\n\n\n')
print('------------------------------------------------------------')
print('below are double column resumes')
print('------------------------------------------------------------')
directory = "double_column_resumes"
for filename in os.listdir(directory):
    file_path = os.path.join(directory, filename)
    if os.path.isfile(file_path) and filename != ".DS_Store":
        print("filename:", filename)
        doc = fitz.open(file_path)
        formatted_filename = f"{filename:<50.50}"  
        print(f"{formatted_filename} ->", end=" ")
        for i, page in enumerate(doc, start=1):
            column_type = "double" if is_the_double_column_resume(page, footer_margin=0, header_margin=0, no_image_text=False) else "single"
            if i < len(doc):
                print(f"page{i}: {column_type} ||", end=" ")
            else:
                print(f"page{i}: {column_type}")  


