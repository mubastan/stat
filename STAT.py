#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import functools
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from Ann import *

### GLOBAL VARIABLES ###

# min size for the image display panels
WMIN = 650
HMIN = 700

# initial/default brush radius & color (painting)
BRUSH_RADIUS = 10
BRUSH_COLOR = QColor(255, 0, 0, 255)

# brush types
DRAWL = 0       # draw/paint line
DRAWELL = 1     # draw/paint filled ellipse--circle
DRAWRECT = 2    # paint filled rectangle
DRAWRECTR = 3   # paint filled rounded rectangle
DRAWPOLY = 4    # paint filled rounded rectangle
BRUSH_TYPES_STR = ["Line", "Circle", "Rectangle", "Rounded rect.", "Polygon"]
BRUSH_TYPES_INT = [DRAWL, DRAWELL, DRAWRECT, DRAWRECTR, DRAWPOLY]


###  FUNCTIONS AND CLASSES ###

# ObjectItem corresponds to Object in Ann.py
class ObjectItem(QGraphicsItem):
    def __init__(self, qimage, x, y, scene, id, opacity, drawMBR):
        
        super(ObjectItem, self).__init__(None, scene)
        
        self.scene = scene
        self.image = qimage
        self.setPos(QPointF(x,y))
        self.ID = id    # this ID is the same as the one in Object.id in Ann.py
        self.rect = QRectF(0,0, qimage.width(), qimage.height())        
        self.rcolor = QPen(Qt.magenta)
        self.opacity = opacity
        self.drawMBR = drawMBR
        self.setFlags(QGraphicsItem.ItemIsSelectable|QGraphicsItem.ItemIsFocusable)
        self.setSelected(True)
        self.setFocus()       
    
    def boundingRect(self):
        return self.rect.adjusted(-2, -2, 2, 2)
    
    def paint(self, painter, option, widget=None):
        painter.setOpacity(self.opacity)
        if self.image:
            painter.drawImage(0,0, self.image)
        if not self.drawMBR: return
        painter.setOpacity(1.0)
        pen = QPen(Qt.magenta)
        pen.setStyle(Qt.DotLine)
        pen.setWidth(2)        
        if option.state & QStyle.State_Selected: 
            pen.setStyle(Qt.SolidLine)
            pen.setWidth(3)            
        painter.setPen(pen)
        painter.drawRect(self.rect)        
        
    def contextMenuEvent(self, event):        
        cmenu = QMenu()
        cmenu.addAction("Update label", self.updateLabel)
        cmenu.addAction("Delete object", self.delete)
        cmenu.addSeparator()
        cmenu.addAction("Increase opacity", self.increaseOpacity)
        cmenu.addAction("Decrease opacity", self.decreaseOpacity)
        cmenu.exec_(event.screenPos())
    
    def updateLabel(self):
        self.scene.updateObjectLabel(self)    
    def delete(self):
        self.scene.deleteObject(self)       
    def increaseOpacity(self):
        self.changeOpacity(0.1)
    def decreaseOpacity(self):
        self.changeOpacity(-0.1)
    def changeOpacity(self, incr):
        self.opacity += incr
        if self.opacity > 1.0: self.opacity = 1.0
        elif self.opacity < 0.1: self.opacity = 0.1
        self.update()
    
class ImageDrawScene(QGraphicsScene):
    def __init__(self, main):
        super(ImageDrawScene, self).__init__()
        self.main = main
        self.backgroundImage = None
        self.foregroundImage = None
        self.setSceneRect(0, 0, WMIN, HMIN)        
        self.w, self.h = 1,1
        self.mpos = QPoint(WMIN/2, HMIN/2)
        
        # painting related
        self.showBrush = True
        self.opacity = 0.7
        self.x0, self.y0 = -1, -1
        self.painting = False
        self.erasing = False
        self.dradius = BRUSH_RADIUS       # drawing/painting radius
        self.dtype = DRAWL                # brush type: line, circle, rectangle, polygon
        self.dcolor = BRUSH_COLOR
        self.dbrush = QBrush(self.dcolor)
        self.pen = QPen(Qt.SolidLine)
        self.pen.setColor(self.dcolor)
        self.pen.setWidth(2*self.dradius)
        self.pen.setCapStyle(Qt.RoundCap)
        
        self.polypen = QPen(Qt.SolidLine)
        self.polypen.setColor(self.dcolor)
        self.polypen.setWidth(3)
        self.polypen.setCapStyle(Qt.RoundCap)
        
        self.polygon = QPolygonF()
        self.polyDrawing = False
        self.polyLast = None        
        self.setBrushType(BRUSH_TYPES_INT[0])
        
    def setRadius(self, radius):
        self.dradius = radius
        self.pen.setWidth(2*self.dradius)
        self.update()
    
    def setBrushType(self, dtype):
        if dtype in BRUSH_TYPES_INT:
            self.dtype = dtype
            if(self.dtype == DRAWPOLY):
                self.startPolygon()
        self.update()
        
    def setBrushColor(self, dcolor):
        self.dcolor = dcolor
        self.dbrush.setColor(self.dcolor)
        self.pen.setColor(self.dcolor)
        self.polypen.setColor(self.dcolor)
        self.update()
    
    def setImage(self, image):
        if image:            
            self.w, self.h = image.width(), image.height()
            self.setBackground(image)
            self.setForeground(self.w, self.h)
            self.setSceneRect(0, 0, self.w, self.h)            
        else:
            self.setSceneRect(0, 0, WMIN, HMIN)
        self.update()
    
    def setForeground(self, w, h):        
        #self.foregroundImage = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        self.foregroundImage = QImage(w, h, QImage.Format_ARGB32)
        self.foregroundImage.fill(QColor(0, 0, 0, 0).rgba())        
    # reset painting
    def resetForeground(self):
        if self.w > 1 and self.h > 1:
            self.setForeground(self.w, self.h)
        if self.dtype == DRAWPOLY:
            self.startPolygon()
        self.update()
    def addObject(self):
        self.main.addObject()
        if self.dtype == DRAWPOLY:
            self.startPolygon()            
        self.update()
    # return the selected object as a single channel image
    def getObjectMask(self):
        if self.foregroundImage:
            return self.foregroundImage.alphaChannel()
        else: return None
    
    def setBackground(self, image):
        if image:
            self.backgroundImage = image.copy()            
            self.update()
    
    # overridden
    def drawForeground (self, painter, rect):
        if self.dtype == DRAWPOLY and self.polyDrawing:
            self.drawPolygon(painter)
        if self.foregroundImage:
            painter.setOpacity(self.opacity)
            painter.drawImage(0, 0, self.foregroundImage)
        if self.showBrush: self.drawCursor(painter)
    
    def drawPolygon(self, painter):
        n = self.polygon.size()        
        painter.setPen(self.polypen)
        if n == 0:
            if self.polyLast: painter.drawEllipse(self.polyLast, 3, 3)
            return
        if self.polyLast:
            self.polygon.append(self.polyLast)
        n = self.polygon.size()
        painter.drawPolygon(self.polygon)  
        for i in range(n):
            painter.drawEllipse(self.polygon.at(i), 3, 3)
        if self.polyLast:
            self.polygon.remove(n-1)
            self.polyLast = None
    # overridden
    def drawBackground (self, painter, rect):
        if self.backgroundImage:
            painter.drawPixmap(0, 0, self.backgroundImage)
    
    def contextMenuEvent(self, event):        
        cmenu = QMenu()
        if self.dtype == DRAWPOLY and self.polyDrawing:
            cmenu.addAction("End polygon", self.endPolygon)
            cmenu.addSeparator()
        cmenu.addAction("Add object", self.addObject)
        cmenu.addAction("Reset/clear", self.resetForeground)
        cmenu.addSeparator()
        if self.erasing:
            cmenu.addAction("Change mode to: paint", self.togglePaintErase)
        else:
            cmenu.addAction("Change mode to: erase", self.togglePaintErase)
        cmenu.addSeparator()
        if self.dtype != DRAWPOLY:
            if self.showBrush: cmenu.addAction("Hide brush", self.toggleBrushFlag)
            else: cmenu.addAction("Show brush", self.toggleBrushFlag)        
        cmenu.addAction("Increase opacity", self.increaseOpacity)            
        cmenu.addAction("Decrease opacity", self.decreaseOpacity)            
        cmenu.exec_(event.screenPos())
        super(ImageDrawScene, self).contextMenuEvent(event)
    def toggleBrushFlag(self):
        self.showBrush = not self.showBrush
        self.update()
    def togglePaintErase(self):
        self.erasing = not self.erasing
        if self.erasing:
            self.dbrush.setColor(QColor(0, 0, 0, 0))
            self.pen.setColor(QColor(0, 0, 0, 0))            
        else:
            self.dbrush.setColor(self.dcolor)
            self.pen.setColor(self.dcolor)            
        self.update()
    def startPolygon(self):
        self.polygon.clear()
        self.polyDrawing = True
        self.update()
    def endPolygon(self):
        self.polyDrawing = False
        self.drawPolygonOnImage()
        self.update()
    def increaseOpacity(self):
        self.changeOpacity(0.1)
    def decreaseOpacity(self):
        self.changeOpacity(-0.1)
    def changeOpacity(self, incr):
        self.opacity += incr
        if self.opacity > 1.0: self.opacity = 1.0
        elif self.opacity < 0.1: self.opacity = 0.1
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.dtype == DRAWPOLY and self.polyDrawing:
                self.polygon.append(event.scenePos())
                self.polyLast = None
            else:
                self.painting = True
                self.drawOnImage(event, self.dtype)                       
            self.update()
        
    def mouseReleaseEvent(self, event):
        if self.dtype == DRAWPOLY: return
        if event.button() == Qt.LeftButton:
            self.painting = False
            self.x0, self.y0 = -1,-1
            self.update()
        
    def mouseMoveEvent (self, event):
        if self.dtype == DRAWPOLY:
            if self.polyDrawing:
                self.polyLast = event.scenePos()
                self.update()
            return
        self.mpos = event.scenePos()
        if self.painting:
            self.drawOnImage(event, self.dtype)
        self.update()  
        
    def drawOnImage(self, event, dtype = DRAWELL):
        if not (self.foregroundImage and self.backgroundImage): return
        pos = event.scenePos()
        x, y = pos.x(), pos.y()            
        painter = QPainter(self.foregroundImage)
        if self.erasing: 
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
        if dtype == DRAWL: painter.setPen(self.pen)
        else:
            painter.setPen(Qt.NoPen)        
            painter.setBrush(self.dbrush)            
        if dtype == DRAWELL:
            painter.drawEllipse(pos, self.dradius, self.dradius)       
        elif dtype == DRAWRECT:            
            painter.drawRect(x-self.dradius, y-self.dradius, 2*self.dradius, 2*self.dradius)
        elif dtype == DRAWRECTR:
            painter.drawRoundedRect(x-self.dradius, y-self.dradius, 2*self.dradius, 2*self.dradius, 25.0, 25.0, mode=Qt.RelativeSize)
        elif dtype == DRAWL and self.x0 >= 0 and self.y0 >= 0:            
            painter.drawLine(self.x0, self.y0, x, y)
        self.x0, self.y0 = x, y
            
        painter.end()
    
    def drawPolygonOnImage(self):
        if self.polygon.size() < 3 or not (self.foregroundImage and self.backgroundImage): return
        painter = QPainter(self.foregroundImage)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.dbrush)
        painter.drawPolygon(self.polygon)
        painter.end()
    # draw the current brush    
    def drawCursor(self, painter):
        painter.setPen(Qt.black)
        if self.erasing: painter.setBrush(Qt.white)
        else: painter.setBrush(self.dbrush)
        if self.dtype == DRAWELL or self.dtype == DRAWL:
            painter.drawEllipse(self.mpos, self.dradius, self.dradius)
        elif self.dtype == DRAWRECT:            
            painter.drawRect(self.mpos.x()-self.dradius, self.mpos.y()-self.dradius, 2*self.dradius, 2*self.dradius)
        elif self.dtype == DRAWRECTR:
            painter.drawRoundedRect(self.mpos.x()-self.dradius, self.mpos.y()-self.dradius, 2*self.dradius, 2*self.dradius, 25.0, 25.0, mode=Qt.RelativeSize)    
            
        
        
# scene to store the list of selected objects, to be shown on the left
class ObjectListScene(QGraphicsScene):
    def __init__(self, main):
        super(ObjectListScene, self).__init__()
        self.main = main                            # main window
        self.backgroundImage = None
        self.setSceneRect(0, 0, WMIN, HMIN)
        self.objID = -1
        self.opacity = 0.6
        self.drawMBR = True
        
        self.selectionChanged.connect(self.objectSelected)
    
    def addObjectImage(self, qimg, x, y):
        self.clearSelection()
        self.objID = self.main.ann.getID()
        item = ObjectItem(qimg, x, y, self, self.objID, self.opacity, self.drawMBR)     # create and add the object, no need to use addItem
        self.update()
    
    def objectSelected(self):
        #print 'Selection Changed'
        items = self.selectedItems()
        if len(items)==0:
            self.main.updateSelectedLabel(None, False)
            return
        for item in items:
            print 'Object ', item.ID, 'selected'
            self.main.updateSelectedLabel(item, True)
            
    # add and display the existing objects
    def addObjects(self, ximage):
        for obj in ximage.objects:
            #if self.objID < obj.id: self.objID = obj.id
            item = ObjectItem(obj.region, obj.x1, obj.y1, self, obj.id, self.opacity, self.drawMBR)
        self.update()    
    
    def updateObjectLabel(self, objectItem):
        if objectItem:            
            self.main.updateObjectLabel(objectItem.ID)            
            self.main.updateSelectedLabel(objectItem, flag=True)
                        
    def deleteObject(self, objectItem):
        if objectItem:
            id = objectItem.ID
            self.removeItem(objectItem)
            self.main.ann.deleteObjects([id])
            self.main.imageListTable.updateTableRow(self.main.ann, self.main.ann.index)
            self.update()
        
    def deleteAllObjects(self):
        self.clear()
        self.main.ann.deleteAllObjects()
        self.main.imageListTable.updateTableRow(self.main.ann, self.main.ann.index)
        self.update()
    
    def deleteSelectedObjects(self):
        items = self.selectedItems()
        for item in items:
            self.deleteObject(item)
    
    # set the (background) image of the scene
    def setImage(self, image):
        if image:
            self.backgroundImage = image.copy()
            w,h = image.width(), image.height()
            self.setSceneRect(0, 0, w, h)
            self.update()
        else:
            self.setSceneRect(0, 0, WMIN, HMIN)
    
    # overridden
    def drawBackground (self, painter, rect):
        if self.backgroundImage:
            painter.drawPixmap(0, 0, self.backgroundImage)
    
    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos())
        if item is None:
            cmenu = QMenu()
            cmenu.addAction("Delete all objects", self.deleteAllObjects)
            cmenu.addSeparator()
            if self.drawMBR: cmenu.addAction("Hide MBRs", self.toggleShowMBR)
            else: cmenu.addAction("Show MBRs", self.toggleShowMBR)
            cmenu.addAction("Increase opacity", self.increaseOpacity)            
            cmenu.addAction("Decrease opacity", self.decreaseOpacity)            
            cmenu.exec_(event.screenPos())
        super(ObjectListScene, self).contextMenuEvent(event)
    
    def toggleShowMBR(self):
        self.drawMBR = not self.drawMBR
        for item in self.items():
            item.drawMBR = self.drawMBR
        self.update()
        
    def increaseOpacity(self):
        self.changeOpacity(0.1)
    def decreaseOpacity(self):
        self.changeOpacity(-0.1)
    def changeOpacity(self, incr):
        self.opacity += incr
        if self.opacity > 1.0: self.opacity = 1.0
        elif self.opacity < 0.1: self.opacity = 0.1
        # update all items/objects in the scene
        for item in self.items():
            item.opacity = self.opacity
        self.update()
    
class ImageTable(QTableWidget):
    def __init__(self, rows, columns, main):
        super(ImageTable, self).__init__(rows, columns, main)
        self.main = main
        self.ann = None
        #self.setHorizontalHeaderLabels(["image filename", "objects", "label"])
        self.setHorizontalHeaderLabels(["image filename", "objects"])
        self.resizeColumnsToContents()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        
    def select(self, row, column):
        self.clearSelection()
        self.setCurrentCell(row, column)        
    
    def setBGColor(self, row, column, color):
        item = self.item(row, column)
        item.setBackgroundColor(color) 
    
    def selectionChanged(self, selected, deselected):        
        items = self.selectedItems()
        rows = []
        for item in items:
            r,c = item.row(), item.column()            
            if c == 0 and r not in rows: rows.append(r)
        if len(rows) == 1:      # only one row is selected, go to that image
            self.main.toImage(rows[0])
    
#    def contextMenuEvent(self, event):
#        if not self.main.ann: return
#        menu = QMenu()
#        for text, label in (
#                ("Positive", 1),
#                ("Negative", -1),
#                ("Skip", 0),
#                ("Positive all", 2),
#                ("Negative all", -2),
#                ("Skip all", 10)):
#            wrapper = functools.partial(self.setLabel, label, text)
#            if label == 2: menu.addSeparator()
#            menu.addAction(text, wrapper)        
#        menu.exec_(event.globalPos())
    
    def setLabel(self, label, text):
        pass
#        self.main.ann.setLabel(label)
#        if label in (-2, 10, 2):
#            print 'Labels: ', text
#            self.updateTableView(self.ann)
#        else:            
#            index = self.main.ann.index        
#            print 'Image', index, 'label:', text
#            self.updateTableRow(self.ann, index)            
    
    # populate the table with the images
    def updateTableView(self, annotation):
        if annotation is None: return
        if annotation.numImages() > 0:
            self.clearContents()
            self.setRowCount(annotation.numImages())
        
        for i in range(annotation.numImages()):
            self.updateTableRow(annotation, i)
        
        self.ann = annotation
        self.resizeColumnsToContents()
    
    def updateTableRow(self, annotation, index):
        if annotation is None: return
        nameItem = QTableWidgetItem(annotation.imageName(index))
        numItem = QTableWidgetItem(str(annotation.numObjects(index)))
        #labelItem = QTableWidgetItem(str(annotation.image(index).label))
        self.setItem(index, 0, nameItem)
        self.setItem(index, 1, numItem)
        #self.setItem(index, 2, labelItem)
        self.update()
    def updateTableRowCol(self, annotation, row, col=1):
        if annotation is None: return        
        numItem = QTableWidgetItem(str(annotation.numObjects(row)))        
        self.setItem(row, col, numItem)
        self.update()

class GraphicsView(QGraphicsView):

    def __init__(self, parent, dragMode=QGraphicsView.NoDrag):
        super(GraphicsView, self).__init__(parent)        
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode (dragMode) 
        self.scene = parent
        self.fitImageView()       
        self.fitmode = True
        
    # Ctrl + wheel to zoom in/out
    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            factor = 1.41 ** (event.delta() / 240.0)            
            self.scale(factor, factor)            
    
    def mouseDoubleClickEvent(self, event):
        self.fitOrResetView()
        super(GraphicsView, self).mouseDoubleClickEvent(event)
    
    def fitOrResetView(self):
        self.fitmode = not self.fitmode
        if self.fitmode: 
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            print 'Fit the image in view'
        else:
            self.resetTransform()
            print 'Actual image size'
    
    def fitImageView(self):
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio) 

# main window containing all the widgets
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.createMenus()
        
        # annotations, image list, etc.
        self.ann = None
        self.imageDir = None
        # current image shown
        piximage = None
        self.startUp = True
        
        ## drawing scene and view on the left
        self.sceneDraw = ImageDrawScene(self)
        self.sceneDraw.setBackground(piximage)        
        self.viewDraw = GraphicsView(self.sceneDraw, QGraphicsView.NoDrag)
        self.viewDraw.installEventFilter(self)
        self.viewDraw.setStatusTip('Painting area: draw/select objects here')
        
        ## list of objects scene and view on the right
        self.sceneList = ObjectListScene(self)
        self.sceneList.setImage(piximage)        
        self.viewList = GraphicsView(self.sceneList, QGraphicsView.RubberBandDrag)
        self.viewList.setRubberBandSelectionMode(Qt.ContainsItemShape)
        self.viewList.installEventFilter(self)
        self.viewList.setStatusTip('List of already selected objects')
        
        ## list of images
        self.imageListTable = ImageTable(10, 2, self)
        
        # text fields for class/subclass name
        imageDirLabel = QLabel("Image Directory:")
        outputAnnDirLabel = QLabel("Output (Annotation) Directory:")
        self.imageDirText = QLineEdit(".../Image/Directory/...")
        self.outputAnnDirText = QLineEdit(".../Output/Directory/...")        
        #self.connect(self.imageDirText, SIGNAL('editingFinished()'), self.updateImageDirText)
        #self.connect(self.outputAnnDirText, SIGNAL('editingFinished()'), self.updateImageDirText)
        
        buttonAnnDir = QPushButton("Change/load...", self)
        buttonAnnDir.setStatusTip('Change the image directory, load image list and re-start annotation')
        self.connect(buttonAnnDir,  SIGNAL('clicked()'), self.loadImageDir)
        
        labelTextLabel = QLabel("Label for the last/selected object:")
        self.currentLabelText = QLineEdit("__none__")
        self.currentLabelText.setStatusTip('Enter new label for the selected object and press Enter to update the label')
        self.connect(self.currentLabelText, SIGNAL('editingFinished()'), self.updateSelectedObjectLabel)
        
        ## buttons
        buttonPrev = QPushButton("Previous", self)
        buttonPrev.setIcon(QIcon('./icons/prev.png'))
        buttonPrev.setStatusTip('Save and go to the previous image  [ shortcut: Ctrl + Space ]')
        buttonPrev.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_Space))
        self.connect(buttonPrev,  SIGNAL('clicked()'), self.onButtonPrev)
        
        buttonNext = QPushButton("Next", self)
        buttonNext.setIcon(QIcon('./icons/next.png'))
        buttonNext.setStatusTip('Save and go to the next image  [ shortcut: Space ]')
        buttonNext.setShortcut(QKeySequence(Qt.Key_Space))
        self.connect(buttonNext,  SIGNAL('clicked()'), self.onButtonNext)
        
#        buttonAddObject = QPushButton("Add", self)
#        buttonAddObject.setIcon(QIcon('./icons/add.png'))
#        buttonAddObject.setStatusTip('Add the selected object  [ shortcut: Ctrl + A ]')
#        buttonAddObject.setShortcut(QKeySequence("Ctrl+a"))     
#        self.connect(buttonAddObject,  SIGNAL('clicked()'), self.onButtonAddObject)
#        
#        buttonDeleteObject = QPushButton("Delete", self)
#        buttonDeleteObject.setIcon(QIcon('./icons/delete.png'))
#        buttonDeleteObject.setStatusTip('Delete the selected object(s)     [ shortcut: Del ]')
#        buttonDeleteObject.setShortcut(QKeySequence(QKeySequence.Delete))               # Delete key
#        self.connect(buttonDeleteObject,  SIGNAL('clicked()'), self.onButtonDeleteObject)
#        
#        buttonResetPaint = QPushButton("Reset", self)
#        buttonResetPaint.setIcon(QIcon('./icons/refresh.png'))
#        buttonResetPaint.setStatusTip('Clear/reset the painting on the right image')
#        self.connect(buttonResetPaint,  SIGNAL('clicked()'), self.onButtonResetPaint)
        
        buttonSave = QPushButton("Save", self)
        buttonSave.setIcon(QIcon('./icons/save.png'))
        buttonSave.setStatusTip('Save annotations/masks for current image   [ shortcut: Ctrl + S ]')
        buttonSave.setShortcut(QKeySequence(QKeySequence.Save))                 # Ctrl + S
        self.connect(buttonSave,  SIGNAL('clicked()'), self.onButtonSave)
        
        buttonExit = QPushButton("Exit", self)
        buttonExit.setIcon(QIcon('./icons/exit.png'))
        buttonExit.setStatusTip('Exit the application    [ shortcut: Ctrl + Q ]')
        self.connect(buttonExit,  SIGNAL('clicked()'), self.close)
        
        # drawing/painting/brush type combo box
        dtypeComboBox = QComboBox()
        # BRUSH_TYPES_STR = [ "Line", "Ellipse", "Rectangle", "Rounded rectangle"] --- global variable
        dtypeComboBox.addItems(BRUSH_TYPES_STR)        
        dtypeComboBox.setStatusTip('Brush type for painting on the image')
        self.connect(dtypeComboBox,  SIGNAL('activated(int)'), self.changeBrushType)
        typeLabel = QLabel("&Brush type:")
        typeLabel.setBuddy(dtypeComboBox)
                
        self.buttonBrushColor = QPushButton("Brush color", self)
        self.buttonBrushColor.setIcon(QIcon(self.getColorRectImage(BRUSH_COLOR)))
        self.brushColor = BRUSH_COLOR
        self.buttonBrushColor.setStatusTip('Select brush color')
        self.connect(self.buttonBrushColor,  SIGNAL('clicked()'), self.changeBrushColor)
        
        ## slider for brush size 
        brushSizeSlider = QSlider(Qt.Horizontal, self)
        brushSizeSlider.setMinimum(1)
        brushSizeSlider.setMaximum(100)
        brushSizeSlider.setTickPosition(QSlider.TicksAbove)
        brushSizeSlider.setTickInterval(10)
        brushSizeSlider.setSingleStep(1)
        brushSizeSlider.setValue(BRUSH_RADIUS)
        self.changeBrushRadius(BRUSH_RADIUS)
        brushSizeSlider.setStatusTip('Brush radius, for painting on the left image')        
        self.connect(brushSizeSlider,  SIGNAL('valueChanged(int)'), self.changeBrushRadius)
        
        ## status bar
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        
        ### Layouts ### 
        # images & image list in the center
        layoutC = QHBoxLayout()        
        layoutC.addWidget(self.viewDraw)        
        layoutC.addSpacing(20)
        layoutC.addWidget(self.viewList)
        layoutC.addSpacing(20)
        
        layoutR00 = QHBoxLayout()        
        layoutR00.addWidget(imageDirLabel) 
        layoutR00.addSpacing(5)
        layoutR00.addWidget(self.imageDirText)
        layoutR00.addSpacing(5)
        layoutR00.addWidget(buttonAnnDir)
        layoutR00.addStretch(0)
        
        layoutR01 = QHBoxLayout()
        layoutR01.addWidget(outputAnnDirLabel)  
        layoutR01.addSpacing(5)
        layoutR01.addWidget(self.outputAnnDirText)
        layoutR01.addStretch(0)
        
        layoutR1 = QHBoxLayout()
        layoutR1.addWidget(typeLabel)
        layoutR1.addSpacing(10)
        layoutR1.addWidget(dtypeComboBox)
        layoutR1.addSpacing(10)
        layoutR1.addWidget(self.buttonBrushColor)
        layoutR1.addStretch(0)
        
        layoutR = QVBoxLayout()
        layoutR.addItem(layoutR00)
        layoutR.addItem(layoutR01)
        layoutR.addSpacing(10)
        layoutR.addWidget(self.imageListTable)
        layoutR.addSpacing(10)        
        layoutR.addItem(layoutR1)
        layoutR.addSpacing(5)
        layoutR.addWidget(brushSizeSlider)
                
        layoutC.addItem(layoutR)
        
        # layout for controls at the bottom
        layoutB = QHBoxLayout()
        layoutB.addWidget(buttonPrev)
        layoutB.addSpacing(20)
        layoutB.addWidget(buttonNext)
        layoutB.addSpacing(60)
        layoutB.addWidget(labelTextLabel)        
        layoutB.addSpacing(20)
        layoutB.addWidget(self.currentLabelText)
#        layoutB.addSpacing(20)        
#        layoutB.addWidget(buttonResetPaint)
        layoutB.addStretch(0)        
        layoutB.addWidget(buttonSave)
        layoutB.addSpacing(20)        
        layoutB.addWidget(buttonExit)
        layoutB.addStretch(0)        
                
        layout = QVBoxLayout()
        layout.addItem(layoutC)
        layout.addSpacing(10)
        layout.addItem(layoutB)
        
        self.widget = QWidget()
        self.widget.setLayout(layout)        
        self.setCentralWidget(self.widget)
        
        self.setWindowTitle("STAT : Scene Text Annotation Tool")
        self.setWindowIcon(QIcon('./icons/stat.png'))        
        
        self.statusMessage("ImAnT ready. Browse an image directory to get started [File/Ctrl-O]")
            
    def createMenus(self):
        menuBar = self.menuBar()
        
        ## File menu
        self.fileMenu = menuBar.addMenu("&File")
        
        self.fileOpenImageDir = QAction("&Open image directory..", self, shortcut="Ctrl+O", triggered=self.loadImageDir)
        self.fileOpenImageDir.setStatusTip("Select the directory containing the images to annotate")
        self.fileMenu.addAction(self.fileOpenImageDir)
        
        self.changeAnnDir = QAction("Change output directory..", self, triggered=self.changeAnnotationDir)
        self.changeAnnDir.setStatusTip("Change the current output directory to any directory")
        self.fileMenu.addAction(self.changeAnnDir)
        
        self.fileMenu.addSeparator()
        
        self.saveBBox = QAction("Save all annotation bboxes", self, triggered=self.onSaveBBox)
        self.saveBBox.setStatusTip("Save all current objects to image.bbox.txt files")
        self.fileMenu.addAction(self.saveBBox)
        
        self.saveAll = QAction("Save all", self, triggered=self.onButtonSave)
        self.saveAll.setStatusTip("Save annotation list and current objects to default files")
        self.fileMenu.addAction(self.saveAll)
        
        #self.saveAnnAs = QAction("Save a copy of annotation list as..", self, triggered=self.saveAnnotationAs)
        #self.saveAnnAs.setStatusTip("Save a copy of annotation list to a specified file")
        #self.fileMenu.addAction(self.saveAnnAs)
        
        #self.fileMenu.addSeparator()
        
        #self.loadAnn = QAction("Load annotation list..", self, triggered=self.loadAnnotation)
        #self.loadAnn.setStatusTip("Load existing annotation list from file")
        #self.fileMenu.addAction(self.loadAnn)
        
        self.fileMenu.addSeparator()
        
        self.fileExitAct = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.fileExitAct.setStatusTip("Exit the application!")
        self.fileMenu.addAction(self.fileExitAct)
        
        self.helpMenu = menuBar.addMenu("&Help")
        self.helpAbout = QAction("&About", self, triggered=self.helpAbout)
        self.helpMenu.addAction(self.helpAbout)   
    
    ### ### ### Event handling    ### ### ###
    
    # handle previous/next image button events
    def onButtonPrev(self):
        ind = self.ann.prev()
        if ind != self.ann.index:
            self.imageListTable.select(ind, 0)
    def onButtonNext(self):
        ind = self.ann.next()
        if ind != self.ann.index:
            self.imageListTable.select(ind, 0)
            
    def onButtonAddObject(self):
        self.addObject()
    def onButtonDeleteObject(self):
        self.sceneList.deleteSelectedObjects()
    def onButtonResetPaint(self):
        self.sceneDraw.resetForeground()
    
    def onButtonSave(self):
        if self.ann is not None:
            self.ann.saveCurrentObjectMasks(True)
            self.ann.saveImageAnnAsTxt(True)
            self.ann.toggleSave(False)
        else: print 'Nothing to save!'
    
    def onSaveBBox(self):
        if self.ann is not None:            
            self.ann.saveALLImageAnnAsBoxTxt(True)
            self.ann.toggleSave(False)
        else: print 'Nothing to save!'
    
    def closeEvent(self, event):
        ret = QMessageBox.question(self, "Exit application?", "Exit?", QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            print '\nSave current image and exit..'
            self.onButtonSave()
        elif ret == QMessageBox.No:
            event.ignore()
            print 'Cancel exit.'
            return                
        event.accept()
        print 'Close.\n'
        
    ### FUNCTIONS ###
    # TODO: ask overwrite
    def saveAnnotationAs(self):
        pass
#        if not self.ann: return
#        fileName = QFileDialog.getSaveFileName(self, "Save a copy of annotation list as", self.ann.annotationDir + self.ann.getAnnotationListFile(), "All Files (*);;Text Files (*.txt)")
#        if fileName:
#            self.ann.saveAnnotationListAs(fileName)
    
    def loadAnnotation(self):
        pass
#        if self.ann:
#            ret = QMessageBox.question(self, "Load annotation", "Save current annotations before loading?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
#            if ret == QMessageBox.Yes: self.onButtonSave()
#            elif ret == QMessageBox.Cancel: return       
#        dir = "./"
#        if self.ann: dir = self.ann.annotationDir
#        fileName = QFileDialog.getOpenFileName(self, "Load annotation list from file", dir, "All Files (*);;Text Files (*.txt)")
#        if fileName:
#            print fileName
#            self.ann = Annotation(fileName)
#            self.startUp = True
#            self.updateClassNamesView()
#            self.imageListTable.updateTableView(self.ann)
#            self.imageListTable.select(0,0)
    
    def changeAnnotationDir(self):
        pass
#        if not self.ann: print 'No annotation yet!'; return
#        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
#        directory = QFileDialog.getExistingDirectory(self, "Select output annotation directory", self.ann.annotationDir, options)
#        if directory:
#            self.ann.setAnnotationDir(directory)
    
    def loadImageDir(self):
        if self.ann:
            ret = QMessageBox.question(self, "Load images", "Save current annotations before loading?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if ret == QMessageBox.Yes: self.onButtonSave()
            elif ret == QMessageBox.Cancel: return
        
        if self.imageDir is None: self.imageDir = os.getcwd()
        #self.imageDir = "/home/research/data/MVOD2-phone-query/queries/"
        
        fd = QFileDialog(None, "Select image folder", self.imageDir, "*.jpg")
        #fd = QFileDialog(None, "Select image folder", self.imageDir, "*.jpg")
        fd.setFileMode(QFileDialog.Directory)        
        fd.setNameFilter("*.jpg;;*.png;;*.jpeg;;*.bmp;;*.tiff;;*.*")
        #fd.setNameFilter("*.jpg;;*.png;;*.jpeg;;*.bmp;;*.tiff;;*.*")
        
        if fd.exec_() == QDialog.Rejected: return        
        fileExt = fd.selectedNameFilter()
        
        # load the image file names from the selected directory
        self.ann = Annotation()
        self.ann.loadDir(fd.directory().absolutePath(), fd.selectedNameFilter())
        self.startUp = True
        #self.updateImageDirText()
        self.updateDirectoriesText(self.ann.imageDir, self.ann.annotationDir)
        self.imageListTable.updateTableView(self.ann)
        self.imageListTable.select(0,0)     # select and goto the first image       
               
    def toImage(self, index):
        if self.ann is not None:
            if not self.startUp:
                self.ann.saveCurrentObjectMasks()
                self.ann.saveImageAnnAsTxt()
                self.ann.toggleSave(False)
                #self.ann.deleteObjectMasks()
            index = self.ann.goto(index)
            self.ann.loadImageAnnAsTxt()
            self.ann.loadObjectImages(index, self.brushColor, False)
            self.imageListTable.updateTableRow(self.ann, self.ann.index)
            self.sceneList.clear()
            self.showCurrentImage()
            self.startUp = False
            print '\nImage', index+1
            
    # load the current image from disk and display it
    def showCurrentImage(self):
        if self.ann is not None and self.ann.numImages() > 0:            
            imageFile = self.ann.curImagePath()
            if os.path.exists(imageFile):
                piximage = QPixmap(imageFile)
                self.showImage(piximage)
            else:
                print 'Image', imageFile, 'does not exits!'
    
    def showImage(self, piximage):        
        self.sceneList.setImage(piximage)
        self.sceneList.addObjects(self.ann.image(self.ann.index))
        self.viewList.fitImageView()
        self.sceneList.update()
        self.sceneDraw.setImage(piximage)
        self.viewDraw.fitImageView()
        self.sceneDraw.update()        
    
    # add the selected object to the scene and to the list of annotations
    def addObject(self):
        mask = self.sceneDraw.getObjectMask()       
        x1,y1,w,h = getMBR_numpy(mask)
        if x1 < 0: return
        objImg = self.sceneDraw.foregroundImage.copy(x1, y1, w, h)
        self.sceneList.addObjectImage(objImg, x1, y1)
        self.sceneDraw.resetForeground()        
        
        # Get the label of the object from the user, as UTF-8 text
        utfText = None
        text, ok = QInputDialog.getText(self, 'Selection', 'Enter label')
        if ok:
            #utfText = text.toUtf8()
            print 'Object', self.sceneList.objID, 'label:', text.toUtf8()
            self.currentLabelText.setText(text);
        else:
            self.currentLabelText.setText("__none__");
        #self.ann.addObject(mask, objImg, x1, y1, self.sceneList.objID, w, h, utfText)
        self.ann.addObject(mask, objImg, x1, y1, self.sceneList.objID, w, h, text)
        #self.imageListTable.updateTableRow(self.ann, self.ann.index)
        self.imageListTable.updateTableRowCol(self.ann, self.ann.index)
    
    # get new label from the user, via text dialog
    def updateObjectLabel(self, objID):
        utfText = None
        text, ok = QInputDialog.getText(self, 'Update object label', 'Enter new label text:')
        if ok:
            print 'Object', self.sceneList.objID, 'new label:', text.toUtf8()
            self.currentLabelText.setText(text);
            self.ann.images[self.ann.index].setObjectText(objID, text)
        else:
            print 'Object', objID, 'label not updated.'
            return
        
    def updateSelectedLabel(self, item, flag=True):
        if not flag:
            self.currentLabelText.setText("__none__")
            return
        text = self.ann.curImage().getObjectText(item.ID)        
        self.currentLabelText.setText(text);
        #print 'updateSelectedLabel:', text.copy().toUtf8()
    
    def updateSelectedObjectLabel(self):        
        items = self.sceneList.selectedItems()
        if len(items)==0:            
            return
        text = self.currentLabelText.text()
        for item in items:            
            self.ann.images[self.ann.index].setObjectText(item.ID, text)
            print 'Object ', item.ID, 'label updated.'
            
    def updateDirectoriesText(self, imageDir, outDir):
        if imageDir is not None:
            self.imageDirText.setText(imageDir)
        if outDir is not None:
            self.outputAnnDirText.setText(outDir)
            
    def updateImageDirText(self):
        pass
#        className = self.imageDirText.text()#.encode('utf-8')
#        subclassName = self.outputAnnDirText.text()        
#        if len(className) < 1 : className = 'none'
#        if len(subclassName) < 1 : subclassName = 'none'        
#        if self.ann is not None:
#            self.ann.setClassName(className, subclassName)
#        print 'Updated class names and directories'
#        print 'class name:', className.toUtf8()
    
    def updateClassNamesView(self):
        pass
#        className = self.ann.className
#        subclassName = self.ann.subclassName
#        if len(className) < 1 or  className == 'none': self.imageDirText.setText("")            
#        else: self.imageDirText.setText(className)
#        if len(subclassName) < 1 or  subclassName == 'none': self.outputAnnDirText.setText("")            
#        else: self.outputAnnDirText.setText(subclassName)        
    
    def changeBrushRadius(self, value):
        self.sceneDraw.setRadius(value)
    def changeBrushType(self, value):
        self.sceneDraw.setBrushType(BRUSH_TYPES_INT[value])
    
    def getColorRectImage(self, color, w=80, h=60):
        qimage = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        qimage.fill(color.rgba())
        return QPixmap.fromImage(qimage)
        
    def changeBrushColor(self):
        cd = QColorDialog(self.sceneDraw.dcolor)
        cd.setOption(QColorDialog.ShowAlphaChannel, True)
        cd.exec_()
        color = cd.selectedColor()
        self.sceneDraw.setBrushColor(color)
        self.buttonBrushColor.setIcon(QIcon(self.getColorRectImage(color)))
        self.brushColor = color
        
    def statusMessage(self, message):
        self.statusBar.showMessage(message)
    def helpAbout(self):        
        QMessageBox.about(self, "About ImAnT",
                "<b>ImAnT: Simple Image Annotation Tool</b><br>"
                "Author: Muhammet Bastan<br> TOV @ Turgut Özal University <br>mubastan@gmail.com<br>July 2015")
    
if __name__ == "__main__":    
    app = QApplication(sys.argv)
    mainWindow = MainWindow()    
    mainWindow.show()
    #mainWindow.showMaximized()
    sys.exit(app.exec_())