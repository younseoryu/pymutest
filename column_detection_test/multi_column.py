"""
This is an advanced PyMuPDF utility for detecting multi-column pages.
It can be used in a shell script, or its main function can be imported and
invoked as descript below.

Features
---------
- Identify text belonging to (a variable number of) columns on the page.
- Text with different background color is handled separately, allowing for
  easier treatment of side remarks, comment boxes, etc.
- Uses text block detection capability to identify text blocks and
  uses the block bboxes as primary structuring principle.
- Supports ignoring footers via a footer margin parameter.
- Returns re-created text boundary boxes (integer coordinates), sorted ascending
  by the top, then by the left coordinates.

Restrictions
-------------
- Only supporting horizontal, left-to-right text
- Returns a list of text boundary boxes - not the text itself. The caller is
  expected to extract text from within the returned boxes.
- Text written above images is ignored altogether (option).
- This utility works as expected in most cases. The following situation cannot
  be handled correctly:
    * overlapping (non-disjoint) text blocks
    * image captions are not recognized and are handled like normal text

Usage
------
- As a CLI shell command use

  python multi_column.py input.pdf footer_margin

  Where footer margin is the height of the bottom stripe to ignore on each page.
  This code is intended to be modified according to your need.

- Use in a Python script as follows:

  ----------------------------------------------------------------------------------
  from multi_column import column_boxes

  # for each page execute
  bboxes = column_boxes(page, footer_margin=50, no_image_text=True)

  # bboxes is a list of fitz.IRect objects, that are sort ascending by their y0,
  # then x0 coordinates. Their text content can be extracted by all PyMuPDF
  # get_text() variants, like for instance the following:
  for rect in bboxes:
      print(page.get_text(clip=rect, sort=True))
  ----------------------------------------------------------------------------------
"""
import os
import sys
import fitz
from kmeans import kmeans_1d

def is_the_double_column_resume(page, footer_margin=50, header_margin=50, no_image_text=True):
    """Determine bboxes which wrap a column."""
    paths = page.get_drawings()
    bboxes = []

    # path rectangles
    path_rects = []

    # image bboxes
    img_bboxes = []

    # bboxes of non-horizontal text
    # avoid when expanding horizontal text boxes
    vert_bboxes = []

    # compute relevant page area
    clip = +page.rect
    clip.y1 -= footer_margin  # Remove footer area
    clip.y0 += header_margin  # Remove header area

    def can_extend(temp, bb, bboxlist):
        """Determines whether rectangle 'temp' can be extended by 'bb'
        without intersecting any of the rectangles contained in 'bboxlist'.

        Items of bboxlist may be None if they have been removed.

        Returns:
            True if 'temp' has no intersections with items of 'bboxlist'.
        """
        for b in bboxlist:
            if not intersects_bboxes(temp, vert_bboxes) and (
                b == None or b == bb or (temp & b).is_empty
            ):
                continue
            return False

        return True

    def in_bbox(bb, bboxes):
        """Return 1-based number if a bbox contains bb, else return 0."""
        for i, bbox in enumerate(bboxes):
            if bb in bbox:
                return i + 1
        return 0

    def intersects_bboxes(bb, bboxes):
        """Return True if a bbox intersects bb, else return False."""
        for bbox in bboxes:
            if not (bb & bbox).is_empty:
                return True
        return False

    def extend_right(bboxes, width, path_bboxes, vert_bboxes, img_bboxes):
        """Extend a bbox to the right page border.

        Whenever there is no text to the right of a bbox, enlarge it up
        to the right page border.

        Args:
            bboxes: (list[IRect]) bboxes to check
            width: (int) page width
            path_bboxes: (list[IRect]) bboxes with a background color
            vert_bboxes: (list[IRect]) bboxes with vertical text
            img_bboxes: (list[IRect]) bboxes of images
        Returns:
            Potentially modified bboxes.
        """
        for i, bb in enumerate(bboxes):
            # do not extend text with background color
            if in_bbox(bb, path_bboxes):
                continue

            # do not extend text in images
            if in_bbox(bb, img_bboxes):
                continue

            # temp extends bb to the right page border
            temp = +bb
            temp.x1 = width

            # do not cut through colored background or images
            if intersects_bboxes(temp, path_bboxes + vert_bboxes + img_bboxes):
                continue

            # also, do not intersect other text bboxes
            check = can_extend(temp, bb, bboxes)
            if check:
                bboxes[i] = temp  # replace with enlarged bbox

        return [b for b in bboxes if b != None]

    def clean_nblocks(nblocks):
        """Do some elementary cleaning."""

        # 1. remove any duplicate blocks.
        blen = len(nblocks)
        if blen < 2:
            return nblocks
        start = blen - 1
        for i in range(start, -1, -1):
            bb1 = nblocks[i]
            bb0 = nblocks[i - 1]
            if bb0 == bb1:
                del nblocks[i]

        # 2. repair sequence in special cases:
        # consecutive bboxes with almost same bottom value are sorted ascending
        # by x-coordinate.
        y1 = nblocks[0].y1  # first bottom coordinate
        i0 = 0  # its index
        i1 = -1  # index of last bbox with same bottom

        # Iterate over bboxes, identifying segments with approx. same bottom value.
        # Replace every segment by its sorted version.
        for i in range(1, len(nblocks)):
            b1 = nblocks[i]
            if abs(b1.y1 - y1) > 10:  # different bottom
                if i1 > i0:  # segment length > 1? Sort it!
                    nblocks[i0 : i1 + 1] = sorted(
                        nblocks[i0 : i1 + 1], key=lambda b: b.x0
                    )
                y1 = b1.y1  # store new bottom value
                i0 = i  # store its start index
            i1 = i  # store current index
        if i1 > i0:  # segment waiting to be sorted
            nblocks[i0 : i1 + 1] = sorted(nblocks[i0 : i1 + 1], key=lambda b: b.x0)
        return nblocks
    
    # vylabs: check if the bbox center is to the left or right of the page center line
    # vylabs: if left, it's left column. if right, it's right column
    def determine_column(bbox):
        bbox_center = (bbox.x0 + bbox.x1) / 2
        return "left" if bbox_center < center_line else "right"
    
    # # vylabs: determine single or doble column resume
    # def is_double_column_resume(x0_values):
    #     # extract x0 of each bbox to form the dataset for K-means
    #     x0_values = [bbox.x0 for bbox in bboxes]
    #     # handle case with less than 2 bboxes, assuming single-column layout
    #     if len(x0_values) < 2:
    #         return bboxes  # or handle as a special case as needed
    #     # apply K-means clustering on x0 values
    #     centroids, clusters = kmeans_1d(x0_values, k=2)
    #     print('clusters:', clusters)
    #     # determine if it's single or double-column based on centroids difference
    #     # it's double column if centroids diff is larger than 1/4 of page width
    #     # print("page.rect.width:", page.rect.width)
    #     # print("page.rect.width / 4:", page.rect.width / 4)
    #     if abs(centroids[0] - centroids[1]) > page.rect.width / 4:
    #         return True
    #     else:
    #         # even though centroids have a big difference, 
    #         # if the clusters count difference is more than x5 times, consider it as single resume
    #         count_0 = 0
    #         count_1 = 0
    #         for value in clusters:
    #             if value == 0:
    #                 count_0 += 1
    #             elif value == 1:
    #                 count_1 += 1
    #         return False

    # vylabs: determine single or doble column resume
    def is_double_column_resume(x0_values):
        if len(x0_values) < 2:
        # vylabs: not enough data for K-means, default to single column
            return False
        page_width = page.rect.width
        centroids, clusters = kmeans_1d(x0_values, k=2)
        if abs(centroids[0] - centroids[1]) > page_width / 4:
            # vylabs: initial check for double-column layout based on centroids distance
            count_0, count_1 = clusters.count(0), clusters.count(1)
            # vylabs: check for significant outliers that might affect the classification
            if max(count_0, count_1) / min(count_0, count_1) > 5:
                return False  # vylabs: considered as a single-column due to disproportionate cluster sizes
            return True
        else:
            return False  # vylabs: default to single-column if centroids are close

    # extract vector graphics
    for p in paths:
        path_rects.append(p["rect"].irect)
    path_bboxes = path_rects

    # sort path bboxes by ascending top, then left coordinates
    path_bboxes.sort(key=lambda b: (b.y0, b.x0))

    # bboxes of images on page, no need to sort them
    for item in page.get_images():
        img_bboxes.extend(page.get_image_rects(item[0]))

    # blocks of text on page
    blocks = page.get_text(
        "dict",
        flags=fitz.TEXTFLAGS_TEXT,
        clip=clip,
    )["blocks"]

    # Make block rectangles, ignoring non-horizontal text
    for b in blocks:
        bbox = fitz.IRect(b["bbox"])  # bbox of the block

        # ignore text written upon images
        if no_image_text and in_bbox(bbox, img_bboxes):
            continue

        # confirm first line to be horizontal
        line0 = b["lines"][0]  # get first line
        if line0["dir"] != (1, 0):  # only accept horizontal text
            vert_bboxes.append(bbox)
            continue

        srect = fitz.EMPTY_IRECT()
        for line in b["lines"]:
            lbbox = fitz.IRect(line["bbox"])
            text = "".join([s["text"].strip() for s in line["spans"]])
            if len(text) > 1:
                srect |= lbbox
        bbox = +srect

        if not bbox.is_empty:
            bboxes.append(bbox)

    # Sort text bboxes by ascending background, top, then left coordinates
    bboxes.sort(key=lambda k: (in_bbox(k, path_bboxes), k.y0, k.x0))

    # Extend bboxes to the right where possible
    bboxes = extend_right(
        bboxes, int(page.rect.width), path_bboxes, vert_bboxes, img_bboxes
    )

    # immediately return of no text found
    if bboxes == []:
        return []

    # --------------------------------------------------------------------
    # Join bboxes to establish some column structure
    # --------------------------------------------------------------------
    # the final block bboxes on page
    nblocks = [bboxes[0]]  # pre-fill with first bbox
    bboxes = bboxes[1:]  # remaining old bboxes

    # vylabs: Calculate the center line of the page
    center_line = page.rect.width / 2

    # vylabs: determine if resume is single column or double column
    all_x0_values = [bbox.x0 for bbox in bboxes]
    is_double_column = is_double_column_resume(all_x0_values)

    return is_double_column
  
    # for i, bb in enumerate(bboxes):  # iterate old bboxes
    #     check = False  # indicates unwanted joins

    #     # check if bb can extend one of the new blocks
    #     for j in range(len(nblocks)):
    #         nbb = nblocks[j]  # a new block

    #         # # never join across columns
    #         # if bb == None or nbb.x1 < bb.x0 or bb.x1 < nbb.x0:
    #         #     continue

    #         # # never join across different background colors
    #         # if in_bbox(nbb, path_bboxes) != in_bbox(bb, path_bboxes):
    #         #     continue

    #         # vylabs: if single column resume, join across columns.
    #         # vylabs: if double column resume, only join if both blocks are in the same column side
    #         if is_double_column is True:
    #             # vylabs: determine each block's column side
    #             bb_side = determine_column(bb)
    #             nbb_side = determine_column(nbb)

    #             # vylabs: only join if both blocks have the same column side
    #             if bb_side != nbb_side:
    #                 continue

    #         temp = bb | nbb  # temporary extension of new block
    #         check = can_extend(temp, nbb, nblocks)
    #         if check == True:
    #             break

    #     if not check:  # bb cannot be used to extend any of the new bboxes
    #         nblocks.append(bb)  # so add it to the list
    #         j = len(nblocks) - 1  # index of it
    #         temp = nblocks[j]  # new bbox added

    #     # check if some remaining bbox is contained in temp
    #     check = can_extend(temp, bb, bboxes)
    #     if check == False:
    #         nblocks.append(bb)
    #     else:
    #         nblocks[j] = temp
    #     bboxes[i] = None

    # # do some elementary cleaning
    # nblocks = clean_nblocks(nblocks)

    # # vylabs: last step sort to always start the blocks from left column, if the resume is double column resume
    # nblocks.sort(key=lambda bbox: (determine_column(bbox), bbox.y0))

    # # return identified text bboxes
    # return nblocks