# scene-text-annotation-tool-py
STAT: Scene text annotation tool in Python.

STAT is a simple scene text annotation tool (written in Python using PyQT4), to select and annotate objects or text in images. The object/text selection is either by painting over the object with the mouse, or by drawing a polygon. In both cases, the minimum bounding box and the object mask as a bitmap are saved on the disk. The objects can be labeled; the labels can be UTF-8 text (tested only for Turkish). 
Version 0.1 of the tool is developed specifically to annotate scene text regions, but it can also be used to annotate other object categories.
The annotations are saved as text files (+ .png files for object masks). It can be easily modified to save in json, xml or any other format, if needed.

See [STAT-USER-GUIDE.pdf](STAT-USER-GUIDE.pdf) for more information.

References:

M. Bastan, H. Kandemir, B. Cantürk, "MT3S: Mobile Turkish Scene Text-to-Speech System for the Visually Impaired", arXiv:1608.05054, August 2016.
