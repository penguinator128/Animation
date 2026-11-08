# Traces the supplied logo JPG into exact polygons (all edges in the mark are straight).
import cv2, json, sys
img = cv2.imread(sys.argv[1], cv2.IMREAD_GRAYSCALE)
_, bw = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
contours, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
out = []
for i, c in enumerate(contours):
    a = cv2.contourArea(c)
    if a < 150: continue
    poly = cv2.approxPolyDP(c, 1.6, True)[:, 0, :].tolist()
    parent = int(hier[0][i][3])
    out.append({"i": i, "parent": parent, "area": a, "pts": poly})
json.dump({"w": img.shape[1], "h": img.shape[0], "shapes": out}, open(sys.argv[2], "w"))
for s in out: print(s["i"], s["parent"], int(s["area"]), len(s["pts"]), s["pts"][:6])
