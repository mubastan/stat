import os
import glob
import numpy
import scipy

from PyQt4.QtCore import *
from PyQt4.QtGui import *

# whole image annotation labels
LPOS, LNEG, LSKIP = 1, -1, 0

# difficulty level: 
# skip: no label (default)
# simple L1: one object on clean background
# simple L2: multiple objects on clean background
# medium L3: single/multiple objects, but not cluttered
# difficult L4: cluttered
# very difficult L5: very hard or impossible to identify the contents
L0, L1, L2, L3, L4, L5 = 0, 1, 2, 3, 4, 5

# view type:
# skip V0: no label
# good view V1: a typical, easy to recognize view @ zero angle
# moderate V2: at some angle, but clearly visible
# side view V3: side, hard to recognize view
V0, V1, V2, V3 = 0, 1, 2, 3

# set
# S0: skip this image, do not use it
# STR: in the training set
# STS: in the test set
S0, STR, STS = 0, 1, -1

# One object selected by the user
class Object:
    def __init__(self, mask=None, region=None, x1=0, y1=0, id=0, w=0, h=0, text=None ):
        self.mask = mask
        self.region = region        
        self.x1, self.y1, self.w, self.h = x1, y1, w, h
        self.text = text    # the label/name/text of this object
        #if region:
        #    self.w, self.h = region.width(), region.height()
        self.id = id
        self.saveMask = True
        #print 'Label for object ', id, self.text.toUtf8()
        
    def deleteMask(self):
        if not self.mask: return
        m = self.mask
        self.mask = None
        del m
    def loadObjectMask(self, fname, forceLoad=False):
        if self.mask and not forceLoad: return
        if os.path.exists(fname):
            self.mask = QImage(fname)
            self.saveMask = True
        else:
            self.mask = None
            print 'Error! Object mask file does not exist: ', fname         
    def loadObjectImage(self, fname, brushColor, forceLoad=False):
        if self.region and not forceLoad: return
        if not self.mask: self.loadObjectMask(fname)
        if self.mask: self.region = self.getObjectRegion(brushColor)
        else:
            self.region = None
            print 'Could not load object image from mask file ', fname        
    # the image region to be shown on the object list scene
    def getObjectRegion(self, brushColor):
        cmask = self.mask.copy(self.x1, self.y1, self.w, self.h)
        rqimg = QImage(self.w, self.h, QImage.Format_ARGB32_Premultiplied)
        rqimg.fill(brushColor.rgba())
        painter = QPainter(rqimg) 
        painter.setCompositionMode(QPainter.CompositionMode_ColorBurn)     
        painter.drawImage(0,0,cmask)
        painter.end()
        return rqimg    
    def save(self, fname):
        if self.mask and self.saveMask:
            if not self.mask.save(fname):
                print 'Error saving object mask ', self.id, ' to ', fname                
            print 'Object mask saved to ', fname
            self.saveMask = False

# One image, containing the selected objects
class XImage:
    def __init__(self, fname=None, label = LSKIP, set = S0, level = L0):
        self.label = label      # image label: positive/negative/skip
        
        self.fname = fname
        self.objects = []
        
        self.save = False
    
    def numObjects(self):
        return len(self.objects)
    
    # check if this 'id' is used by any object
    def checkID(self, id):
        for obj in self.objects:
            if id == obj.id: return True
        return False
    # return an available id for a new object
    def getID(self):
        id = self.numObjects()
        for i in range(id):
            if self.checkID(i) == False:
                return i            
        return id
    
    def mask(self, index):
        if index < len(self.objects): return self.objects[index].mask
    
    def addObject (self, mask, region, x1, y1, id, w=0, h=0, text=None):
        obj = Object(mask, region, x1, y1, id, w, h, text)
        self.objects.append(obj)
        self.save = True    # image modified, need to save
    
    def deleteObject(self, id):
        for obj in self.objects:
            if id == obj.id:
                self.objects.remove(obj)
                self.save = True    # image modified, need to save
    
    def deleteObjectMasks(self):
        for obj in self.objects:
            obj.deleteMask()
            self.save = True    # image modified, need to save
    
    def deleteAllObjects(self):
        del self.objects[:]
        self.save = True    # image modified, need to save
        
    def getObjectText(self, id):
        for obj in self.objects:
            if obj.id == id:
                return obj.text
        return "__none__"
    
    def setObjectText(self, id, text):
        for obj in self.objects:
            if obj.id == id:
                obj.text = text
                self.save = True    # image modified, need to save
                break
    
    def saveObjectMasks(self, annotationDir):
        for i in range(self.numObjects()):
            imgName = os.path.splitext(self.fname)[0]
            fname = annotationDir + imgName + '.' + str(self.objects[i].id) + '.png'
            self.objects[i].save(fname)
#        # delete unused masks from the disk
#        i = self.numObjects()
#        while True:
#            imgName = os.path.splitext(self.fname)[0]            
#            fname = annotationDir + imgName + '.' + str(i) + '.png'
#            if not os.path.exists(fname): return
#            else: os.remove(fname)
            
    def loadObjectMasks(self, annotationDir, forceLoad=False):
        imgName = os.path.splitext(self.fname)[0]
        for i in range(self.numObjects()):
            fname = annotationDir + imgName + '.' + str(self.objects[i].id) + '.png'
            if os.path.exists(fname):
                self.objects[i].loadObjectMask(fname, forceLoad)
                
    def loadObjectImages(self, annotationDir, brushColor, forceLoad=False):        
        if self.numObjects() == 0: return
        
        imgName = os.path.splitext(self.fname)[0]
        #delList = []
        for i in range(self.numObjects()):
            fname = annotationDir + imgName + '.' + str(self.objects[i].id) + '.png'
            if os.path.exists(fname):
                self.objects[i].loadObjectImage(fname, brushColor, forceLoad)
        #    else: delList.append(self.objects[i].id)                
        #for id in delList:
        #        self.deleteObject(id)
    
    def loadTxtFile(self, annotationDir):
        if self.numObjects() > 0:
            print 'loadTxtFile: image.objects not empty -- no load.'
            return
        
        filePath = annotationDir + self.fname + ".labels.txt"
        if not os.path.exists(filePath): return        
        
        ifs = open(filePath, 'r')
        lines = ifs.readlines()
        for i in range(1,len(lines)):
            sline = lines[i].split()
            
            if len(sline) < 6:
                print 'File', filePath, 'not in correct format. Skip.'
                ifs.close()
                return
            
            id = int(sline[0])
            x1 = int(sline[1])
            y1 = int(sline[2])
            w = int(sline[3])
            h = int(sline[4])
            text = ' '.join(sline[5:])
            #print 'Loaded:', text
            utfstr = QString(unicode(text, 'utf8'))
            obj = Object(None, None, x1, y1, id, w, h, utfstr)
            self.objects.append(obj)
        
        ifs.close()
        print 'Loaded:', filePath
        
    # save annotations for 'imagePath' to 'filePath'
    def toTxtFile(self, annotationDir):
        if self.numObjects()==0: return
    
        filePath = annotationDir + self.fname + ".labels.txt"
        ofs = open(filePath, 'w')
        if not ofs:
            print 'Could not open file', filePath, 'to save image annotation!'
            return
        ofs.write(self.fname)        
        for obj in self.objects:
            ofs.write('\n')
            ofs.write(str(obj.id) + ' ' )
            ofs.write(str(obj.x1) + ' ' )
            ofs.write(str(obj.y1) + ' ' )
            ofs.write(str(obj.w) + ' ' )
            ofs.write(str(obj.h) + ' ' )
            ofs.write(obj.text.toUtf8())
            #ofs.write(obj.text)
        
        ofs.close()
        print 'Saved to:', filePath
    
    # save annotations, bounding boxes, like the output of a text detector (e.g., snoopertext) --> image.png.box.txt
    def toTxtBoxFile(self, imageDir, annotationDir):
        if self.numObjects()==0: return
    
        filePath = annotationDir + self.fname + ".box.txt"
        ofs = open(filePath, 'w')
        if not ofs:
            print 'Could not open file', filePath, 'to save bounding annotation!'
            return
        imagePath = imageDir + self.fname
        ofs.write(imagePath)
        image = QPixmap(imagePath)
        w,h = image.width(), image.height()        
        ofs.write('\n')
        ofs.write(str(w) + ' ' + str(h) )
        for obj in self.objects:
            ofs.write('\n')
            ofs.write(str(obj.x1) + ' ' )
            ofs.write(str(obj.y1) + ' ' )
            ofs.write(str(obj.w) + ' ' )
            ofs.write(str(obj.h) + ' ' )           
        
        ofs.close()
        print 'Saved .box.txt to:', filePath
    
    def toString(self):
        pass
#        lineStr = str(self.set) + ' ' + str(self.level) + ' ' + str(self.label) + ' ' + str(self.numObjects()) + ' ' + self.fname
#        for obj in self.objects:
#            lineStr += ' ' + str(obj.view) + ' ' + str(obj.label) + ' ' + str(obj.x1) + ' ' + str(obj.y1) + ' ' + str(obj.w) + ' ' + str(obj.h)
#        return lineStr
        
# all annotations, list of images + objects + object MBRs        
class Annotation:
    def __init__(self, fname=None):
        
        self.images = []
        self.index = 0      # index of the current image
        
        self.imageDir = None
        self.dirPath = os.getcwd() + '/'
        self.annotationDir = self.dirPath + "ann/"
        self.annfilename = fname
        if fname:
            self.loadAnnotation(fname)
    
    def prev(self):
        ind = self.index - 1
        if ind < 0: ind = 0
        return ind
    def next(self):
        ind = self.index + 1
        if ind >= self.numImages(): ind = self.numImages() - 1
        return ind
    # get an ID for the next object in the current image
    def getID(self):
        return self.curImage().getID()
    
    def goto(self, index):
        if index >= 0 and index < self.numImages(): self.index = index
        return self.index
    def numImages(self):
        return len(self.images)
        
    def image(self, index):
        if index < self.numImages(): return self.images[index]
        else: return None
    def curImage(self):
        return self.image(self.index)
    def imageName(self, index):
        if index < self.numImages(): return self.images[index].fname
        else: return ""
    def curImagePath(self):
        return self.imagePath(self.index)
    def imagePath(self, index):
        if index < self.numImages(): return self.imageDir + self.images[index].fname
        else: return ""
    def numObjects(self, index):
        if index < self.numImages(): return self.images[index].numObjects()
        else: return 0
    
    def setClassName(self, className, subclassName):
        pass
#        self.className = str(className)
#        self.subclassName = str(subclassName)        
#        annDir = str(self.rootPath + 'annotation/')
#        if self.subclassName != "none": annDir += self.subclassName
#        elif self.className != "none": annDir += self.className
#        self.setAnnotationDir(annDir)
        
    def setAnnotationDir(self, dir):
        if not os.path.isdir(dir):            
            os.makedirs(dir)
            print dir, ' did not exist! Created..'
        self.annotationDir = dir + "/"
        print 'Annotation directory changed to : ', self.annotationDir
        #return self.annotationDir
    
    def setLabel(self, label):
        if label in (-1, 0, 1):
            self.curImage().label = label
        elif label in (-2, 10, 2):
            for i in range(self.numImages()):
                if label == -2: label = -1
                elif label == 10: label = 0
                elif label == 2: label = 1
                self.image(i).label = label
    
    # add object to image @index location   
    def addObjectTo(self, index, mask, region, x1, y1, id, w=0, h=0, text=None):
        if index < self.numImages():
            self.images[index].addObject (mask, region, x1, y1, id, w, h, text)
    # add object to current image
    def addObject (self, mask, region, x1, y1, id, w=0, h=0, text=None):
        self.addObjectTo(self.index, mask, region, x1, y1, id, w, h, text)
    
    def deleteAllObjects(self):
        self.deleteAllObjectsAt(self.index)
    def deleteAllObjectsAt(self, index):
        if index < self.numImages(): self.images[index].deleteAllObjects()
    
    def deleteObjectMasks(self):
        self.deleteObjectMasksAt(self.index)
    def deleteObjectMasksAt(self, index):
        if index < self.numImages(): self.images[index].deleteObjectMasks()
        
    def deleteObjects(self, ids):
        self.deleteObjectsAt(self.index, ids)
    def deleteObjectsAt(self, index, ids):
        if index > self.numImages() or len(ids) == 0: return
        self.images[index].loadObjectMasks(self.annotationDir)
        for id in ids:
            self.images[index].deleteObject(id)
        
    def loadDir(self, imageDir, fileExt):
        print 'Image Directory: ', imageDir
        print 'File extension: ', fileExt
        self.imageDir = str(imageDir + '/')
        self.annotationDir = str(imageDir + '/ann/')
        
        self.fex = str(fileExt)
        chain = self.imageDir + str(fileExt)
        print chain
        # get all the files with the given extension (full path)
        imageFiles = glob.glob(chain)
        imageList = []
        # extract only the file names
        for f in imageFiles:
            imageList.append(os.path.basename(f))        
        # sort the file names
        imageList.sort(cmp=lambda x, y: cmp(x.lower(), y.lower()))        
        # add to the list of images
        for f in imageList:
            ximg = XImage(f)
            ximg.loadTxtFile(self.annotationDir)
            self.images.append(ximg)
        print 'Number of images loaded: ', len(self.images)
        #print 'loadDir:', self.annotationDir
        
    # save the selected object masks of the current image as png images
    # in the directory /path/to/data/annotation/
    def saveCurrentObjectMasks(self, forceSave=False):
        if self.images[self.index].save or forceSave:
            self.saveObjectMasks(self.index)
    
    def saveImageAnnAsTxt(self, forceSave=False):
        if self.images[self.index].save or forceSave:
            self.images[self.index].toTxtFile(self.annotationDir)
        else:
            print 'No change to save for image', self.index
    
    def saveImageAnnAsBoxTxt(self, forceSave=False):
        if self.images[self.index].save or forceSave:
            self.images[self.index].toTxtBoxFile(self.imageDir, self.annotationDir)
        else:
            print 'No change to save for image', self.index
    
    # save all the annotations, to .box.txt files
    def saveALLImageAnnAsBoxTxt(self, forceSave=False):
        for i in range(self.numImages()):        
            self.images[i].toTxtBoxFile(self.imageDir, self.annotationDir)        
    
    def toggleSave(self, flag=False):
        self.images[self.index].save = flag
    
    def loadImageAnnAsTxt(self):
        self.images[self.index].loadTxtFile(self.annotationDir)
    
    def saveObjectMasks(self, index):
        if self.numImages() == 0 or index >= self.numImages() : return
        if self.image(index).numObjects() == 0: return
        if not os.path.isdir(self.annotationDir):
            print self.annotationDir, ' does not exist! create it..'
            os.makedirs(self.annotationDir)        
        self.image(index).saveObjectMasks(self.annotationDir)
        print 'Saved object masks (selections)'
        
    # load the already saved object masks from the disk
    def loadObjectMasks(self, index, forceLoad=False):
        if self.numImages() == 0 or index >= self.numImages() : return
        self.images[index].loadObjectMasks(self.annotationDir, forceLoad)
    def loadObjectImages(self, index, brushColor, forceLoad=False):
        if self.numImages() == 0 or index >= self.numImages() : return
        self.images[index].loadObjectImages(self.annotationDir, brushColor, forceLoad)
    
    def getAnnotationListFile(self):
        return None
#        filename = self.folder
#        if len(self.className) > 0 and self.className != 'none': filename += '.' + self.className
#        if len(self.subclassName) > 0 and self.subclassName != 'none': filename += '.' + self.subclassName
#        filename += '.txt'
#        return filename
        
    def saveAnnotationList(self):        
        pass
        #if self.annfilename is None:
        #self.annfilename = self.annotationDir + self.getAnnotationListFile()
        #self.saveAnnotationListAs(self.annfilename)        
    
    def saveAnnotationListAs(self, fname):
        pass
#        if self.numImages() == 0: print 'Nothing to save yet!'; return    
#        ofs = open(fname, 'w')
#        if not ofs: print 'Could not open file to save!'; return    
#        ofs.write( self.className + ' ' + self.subclassName )
#        ofs.write('\n')
#        ofs.write( self.dirPath + ' ' + self.folder )
#        ofs.write('\n')
#        ofs.write( self.annotationDir + ' ' + self.subclassName )
#        ofs.write('\n')
#        ofs.write(str(self.numImages()))        
#        for image in self.images:
#            ofs.write('\n')
#            ofs.write(image.toString())        
#        ofs.close()
#        self.annfilename = fname
#        print 'Annotation list saved to: ', fname
    
    def loadAnnotation(self, fname):
        print 'TBI'
#        ifs = open(fname)
#        if not ifs:
#            print 'Could not load ', fname
#            return
#        line = ifs.readline()
#        self.className, self.subclassName = line.split()
#        line = ifs.readline()
#        self.dirPath, self.folder = line.split()
#        self.rootDir = self.dirPath
#        line = ifs.readline()
#        self.annotationDir = line.split()[0]
#        ifs.readline()
#        # read images and objects
#        for line in ifs:
#            self.images.append(self.parseLine(line))
#        print 'Loaded ', fname
#        print 'Number of images in the annotation list: ', self.numImages()
#        ifs.close()
    
    # initial version
    def parseLine0(self, line):
        tokens = line.split()
        # XImage(self, fname=None, label = LSKIP, set = S0, level = L0)
        ximg = XImage(tokens[2], int(tokens[0]))        
        # objects
        for i in range(int(tokens[1])):
            # Object(self, mask=None, region=None, x1=0, y1=0, id = 0, w = 0, h = 0, view = V0, label = LPOS )
            xobj = Object(None, None, int(tokens[4*i+3]), int(tokens[4*i+4]), i, int(tokens[4*i+5]), int(tokens[4*i+6]) )
            ximg.objects.append(xobj)
        return ximg
    # updated version (22 October 2011)
    def parseLine(self, line):
        tokens = line.split()
        # XImage(self, fname=None, label = LSKIP, set = S0, level = L0)
        ximg = XImage(tokens[4], int(tokens[2]), int(tokens[0]), int(tokens[1]))        
        # objects
        for i in range(int(tokens[3])):
            # Object(self, mask=None, region=None, x1=0, y1=0, id = 0, w = 0, h = 0, view = V0, label = LPOS )
            xobj = Object(None, None, int(tokens[6*i+7]), int(tokens[6*i+8]), i, int(tokens[6*i+9]), int(tokens[6*i+10]), int(tokens[6*i+5]), int(tokens[6*i+6]) )
            ximg.objects.append(xobj)
        return ximg
        
        
#def getMBR_numpy(qimage):
#    x1, y1, x2, y2 = -1, -1, -1, -1
#    if qimage:
#        qimage.save("tmp.png")
#        nimg = scipy.misc.imread('tmp.png')
#        r,c = numpy.where(nimg > 0)
#        if len(r) > 0:      # check if there is any FG pixel
#            x1, y1, x2, y2 = c.min(), r.min(), c.max(), r.max() 
#    return x1, y1, x2-x1+1, y2-y1+1

# by Uwe Schmidt
def getMBR_numpy(qimage):
    x1, y1, x2, y2 = -1, -1, -1, -1
    if qimage:
        fg, x1, y1, x2, y2 = 0, float('inf'), float('inf'), float('-inf'), float('-inf')
        for y in range(qimage.height()):
          for x in range(qimage.width()):
            pcol = qimage.pixel(x,y)
            if qRed(pcol) > 0 or qBlue(pcol) > 0 or qGreen(pcol) > 0 :
              fg = 1; y1 = min(y,y1); x1 = min(x,x1); y2 = max(y,y2); x2 = max(x,x2)
        if fg == 0:
          x1, y1, x2, y2 = -1, -1, -1, -1
        # qimage.save("tmp.png")
        # nimg = scipy.misc.imread('tmp.png')
        # r,c = numpy.where(nimg > 0)
        # if len(r) > 0:      # check if there is any FG pixel
        #     x1, y1, x2, y2 = c.min(), r.min(), c.max(), r.max() 
    return x1, y1, x2-x1+1, y2-y1+1