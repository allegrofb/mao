# -*- coding: utf-8 -*-

# Copyright (c) 2012, Bin Tan
# This file is distributed under the BSD Licence. See python-epub-builder-license.txt for details.

import itertools
import mimetypes
import os
import shutil
import subprocess
import uuid
import zipfile
from genshi.template import TemplateLoader
from lxml import etree

class TocMapNode:
    
    def __init__(self):
        self.playOrder = 0
        self.title = ''
        self.href = ''
        self.children = []
        self.depth = 0
    
    def assignPlayOrder(self):
        nextPlayOrder = [0]
        self.__assignPlayOrder(nextPlayOrder)
    
    def __assignPlayOrder(self, nextPlayOrder):
        self.playOrder = nextPlayOrder[0]
        nextPlayOrder[0] = self.playOrder + 1
        for child in self.children:
            child.__assignPlayOrder(nextPlayOrder)


class EpubItem:

    def __init__(self):
        self.id = ''
        self.srcPath = ''
        self.destPath = ''
        self.mimeType = ''
        self.html = ''
        self.properties = ''

class EpubBook:

    def __init__(self):
        self.loader = TemplateLoader('templates', default_encoding="utf-8")

        self.rootDir = ''
        self.UUID = uuid.uuid1()

        #self.lang = 'en-US'
        self.lang = 'zh-CN'
        self.title = ''
        self.creators = []
        self.metaInfo = []

        self.imageItems = {}
        self.htmlItems = {}
        self.cssItems = {}

        self.coverImage = None
        self.titlePage = None
        self.tocPage = None

        self.spine = []
        self.guide = {}
        self.tocMapRoot = TocMapNode()
        self.lastNodeAtDepth = {0 : self.tocMapRoot}
        
    def setTitle(self, title):
        self.title = title
    
    def setLang(self, lang):
        self.lang = lang
    
    def addCreator(self, name, role = 'aut'):
        self.creators.append((name, role))
        
    def addMeta(self, metaName, metaValue, **metaAttrs):
        self.metaInfo.append((metaName, metaValue, metaAttrs))
    
    def getMetaTags(self):
        l = []
        for metaName, metaValue, metaAttr in self.metaInfo:
            beginTag = '<dc:%s' % metaName
            if metaAttr:
                for attrName, attrValue in metaAttr.iteritems():
                    beginTag += ' opf:%s="%s"' % (attrName, attrValue)
            beginTag += '>'
            endTag = '</dc:%s>' % metaName
            l.append((beginTag, metaValue, endTag))
        return l
        
    def getImageItems(self):
        return sorted(self.imageItems.values(), key = lambda x : x.id)
    
    def getHtmlItems(self):
        return sorted(self.htmlItems.values(), key = lambda x : x.id)

    def getCssItems(self):
        return sorted(self.cssItems.values(), key = lambda x : x.id)
    
    def getAllItems(self):
        return sorted(itertools.chain(self.imageItems.values(), self.htmlItems.values(), self.cssItems.values()), key = lambda x : x.id)
        
    def addImage(self, srcPath, destPath, properties = ''):
        item = EpubItem()
        item.id = 'image_%d' % (len(self.imageItems) + 1)
        item.srcPath = srcPath
        item.destPath = 'img/'+destPath
        #item.mimeType = mimetypes.guess_type(destPath)[0]
        item.mimeType = mimetypes.types_map['.jpg'] #hyjiang
        item.properties = properties
        assert item.destPath not in self.imageItems
        self.imageItems[destPath] = item
        return item
    
    def addHtmlForImage(self, imageItem):
        tmpl = self.loader.load('image.xhtml')
        stream = tmpl.generate(book = self, item = imageItem)
        #html = stream.render('xhtml', doctype = 'xhtml11', drop_xml_decl = False)
        html = stream.render('xhtml', drop_xml_decl = False)
        return self.addHtml('', '%s.xhtml' % imageItem.destPath, html)
    
    def addHtml(self, srcPath, destPath, html, properties = ''):   #hyjiang
        item = EpubItem()
        item.id = 'html_%d' % (len(self.htmlItems) + 1)
        item.srcPath = srcPath
        #item.destPath = 'xhtml/'+destPath  #hyjinag
        item.destPath = destPath
        item.html = html
        item.mimeType = 'application/xhtml+xml'
        item.properties = properties
        assert item.destPath not in self.htmlItems
        self.htmlItems[item.destPath] = item
        return item
    
    def addCss(self, srcPath, destPath):
        item = EpubItem()
        item.id = 'css_%d' % (len(self.cssItems) + 1)
        item.srcPath = srcPath
        item.destPath = 'css/'+destPath
        item.mimeType = 'text/css'
        assert item.destPath not in self.cssItems
        self.cssItems[item.destPath] = item
        return item
    
    def addCover(self, srcPath):
        assert not self.coverImage
        _, ext = os.path.splitext(srcPath)
        destPath = 'cover%s' % ext
        self.coverImage = self.addImage(srcPath, destPath, 'cover-image')
        #coverPage = self.addHtmlForImage(self.coverImage)
        #self.addSpineItem(coverPage, False, -300)
        #self.addGuideItem(coverPage.destPath, 'Cover', 'cover')
        
    def __makeTitlePage(self):
        assert self.titlePage
        if self.titlePage.html:
            return
        tmpl = self.loader.load('title-page.xhtml')
        stream = tmpl.generate(book = self)
        #self.titlePage.html = stream.render('xhtml', doctype = 'xhtml11', drop_xml_decl = False)
        self.titlePage.html = stream.render('xhtml', drop_xml_decl = False)
        
    def addTitlePage(self, html = ''):
        assert not self.titlePage
        self.titlePage = self.addHtml('', 'title-page.xhtml', html)
        self.addSpineItem(self.titlePage, True, -200)
        self.addGuideItem('title-page.xhtml', 'Title Page', 'title-page')
    
    def __makeTocPage(self):
        assert self.tocPage
        tmpl = self.loader.load('toc.xhtml')
        stream = tmpl.generate(book = self)
        #self.tocPage.html = stream.render('xhtml', doctype = 'xhtml11', drop_xml_decl = False)
        self.tocPage.html = stream.render('xhtml', drop_xml_decl = False)

    def addTocPage(self):
        assert not self.tocPage
        self.tocPage = self.addHtml('', 'toc.xhtml', '', 'nav')
        self.addSpineItem(self.tocPage, False, -100)
        self.addGuideItem('toc.xhtml', 'Table of Contents', 'toc')
    
    def getSpine(self):
        return sorted(self.spine)
    
    def addSpineItem(self, item, linear = True, order = None):
        assert item.destPath in self.htmlItems
        if order == None:
            order = (max(order for order, _, _ in self.spine) if self.spine else 0) + 1
        self.spine.append((order, item, linear))
    
    def getGuide(self):
        return sorted(self.guide.values(), key = lambda x : x[2])
    
    def addGuideItem(self, href, title, type):
        assert type not in self.guide
        self.guide[type] = (href, title, type)
    
    def getTocMapRoot(self):
        return self.tocMapRoot
    
    def getTocMapHeight(self):
        return max(self.lastNodeAtDepth.keys())
    
    def addTocMapNode(self, href, title, depth = None, parent = None):
        node = TocMapNode()
        node.href = href
        node.title = title
        if parent == None:
            if depth == None:
                parent = self.tocMapRoot
            else:
                parent = self.lastNodeAtDepth[depth - 1]
        parent.children.append(node)
        node.depth = parent.depth + 1
        self.lastNodeAtDepth[node.depth] = node
        return node
    
    def makeDirs(self):
        try:
            os.makedirs(os.path.join(self.rootDir, 'META-INF'))
        except OSError:
            pass
        try:
            os.makedirs(os.path.join(self.rootDir, 'EPUB'))
        except OSError:
            pass
        try:
            os.makedirs(os.path.join(self.rootDir, 'EPUB\css'))
        except OSError:
            pass
        try: 
            os.makedirs(os.path.join(self.rootDir, 'EPUB\img'))
        except OSError:
            pass   
        #try:
        #    os.makedirs(os.path.join(self.rootDir, r'EPUB\xhtml'))
        #except OSError:
        #    pass
    
    def __writeContainerXML(self):
        fout = open(os.path.join(self.rootDir, 'META-INF', 'container.xml'), 'w', encoding='utf-8', errors='strict')
        tmpl = self.loader.load('container.xml')
        stream = tmpl.generate()
        fout.write(stream.render('xml'))
        fout.close()

    def __writeTocNCX(self):
        self.tocMapRoot.assignPlayOrder()
        #fout = open(os.path.join(self.rootDir, 'EPUB\\xhtml', 'toc.xhtml'), 'w',  encoding='utf-8', errors='strict')  #hyjiang
        fout = open(os.path.join(self.rootDir, 'EPUB', 'toc.xhtml'), 'w',  encoding='utf-8', errors='strict')
        tmpl = self.loader.load('toc.xhtml')
        stream = tmpl.generate(book = self)
        #fout.write(stream.render('xhtml', doctype = 'xhtml11', drop_xml_decl = False))
        fout.write(stream.render('xhtml', drop_xml_decl = False))
        fout.close()
    
    def __writeContentOPF(self):#hyjiang
        fout = open(os.path.join(self.rootDir, 'EPUB', 'package.opf'), 'w',  encoding='utf-8', errors='strict')
        tmpl = self.loader.load('package.opf')
        stream = tmpl.generate(book = self)
        #fout.write(stream.render('xml'))
        fout.write(stream.render('xhtml', drop_xml_decl = False))
        #fout.write(stream.render('xhtml', doctype = 'xhtml11', drop_xml_decl = False))  # <--------------
		
        #from genshi.template.text import NewTextTemplate
        #txtloader = TemplateLoader('templates', default_encoding="utf-8")		
        #tmpl = txtloader.load('content-text.opf', cls=NewTextTemplate)
        #stream = tmpl.generate(book=self)
        #fout.write(stream.render())
		
        fout.close()
    
    def __writeItems(self):
        for item in self.getAllItems():
            print((item.id, item.destPath))
            if item.html:
                fout = open(os.path.join(self.rootDir, 'EPUB', item.destPath), 'w', encoding='utf-8', errors='strict')
                fout.write(item.html)
                fout.close()
            else:
                #print('*****************')
                #print(item)
                shutil.copyfile(item.srcPath, os.path.join(self.rootDir, 'EPUB', item.destPath))


    def __writeMimeType(self):
        fout = open(os.path.join(self.rootDir, 'mimetype'), 'w', encoding='utf-8', errors='strict')
        fout.write('application/epub+zip')
        fout.close()
    
    def createEPUB(self, rootDir, outputPath):
        fout = zipfile.ZipFile(outputPath, 'w')
        cwd = os.getcwd()
        os.chdir(rootDir)
        fout.write('mimetype', compress_type = zipfile.ZIP_STORED)
        fileList = []
        fileList.append(os.path.join('META-INF', 'container.xml'))
        fileList.append(os.path.join('EPUB', 'package.opf'))
        for itemPath in self.getAllItems():
            fileList.append(os.path.join('EPUB', itemPath.destPath))			
        for filePath in fileList:
            fout.write(filePath, compress_type = zipfile.ZIP_DEFLATED)
        fout.close()
        os.chdir(cwd)
	
    @staticmethod
    def __listManifestItems(contentOPFPath):#hyjiang

        tree = etree.parse(contentOPFPath)
        #parser = etree.XMLParser(ns_clean=True,recover=True)
        #tree   = etree.parse(contentOPFPath, parser)	
        #print('********************')
        #print(tree.xpath("//manifest/item/@href", namespaces = {'opf': 'http://www.idpf.org/2007/opf'}))	
        #print(tree.xpath("//opf:manifest/opf:item/@href", namespaces = {'opf': 'http://www.idpf.org/2007/opf'}))
	
        #tree = etree.parse(contentOPFPath)
        #return tree.xpath("//opf:manifest/opf:item/@href", namespaces = {'opf': 'http://www.idpf.org/2007/opf'})
        return tree.xpath("//manifest/item/@href", namespaces = {'opf': 'http://www.idpf.org/2007/opf'})
	
        #content_file=open(os.path.join('OEBPS', 'content.opf'), mode='r', encoding='gbk', errors='strict') 
        #u = content_file.read()
        #s = u.encode('utf-8')
        #content_file.close()
        #utf8_parser = etree.XMLParser(encoding='utf-8')
        #tree = etree.fromstring(s, parser=utf8_parser) 
        #return tree.xpath("//opf:manifest/opf:item/@href", namespaces = {'opf': 'http://www.idpf.org/2007/opf'})
		
    @staticmethod
    def createArchive(rootDir, outputPath):
        fout = zipfile.ZipFile(outputPath, 'w')
        cwd = os.getcwd()
        os.chdir(rootDir)
        fout.write('mimetype', compress_type = zipfile.ZIP_STORED)
        fileList = []
        fileList.append(os.path.join('META-INF', 'container.xml'))
        fileList.append(os.path.join('EPUB', 'package.opf'))
        for itemPath in EpubBook.__listManifestItems(os.path.join('EPUB', 'package.opf')):
            fileList.append(os.path.join('EPUB', itemPath))			
        for filePath in fileList:
            fout.write(filePath, compress_type = zipfile.ZIP_DEFLATED)
        fout.close()
        os.chdir(cwd)
    
    @staticmethod
    def checkEpub(checkerPath, epubPath):
        subprocess.call(['java', '-jar', checkerPath, epubPath], shell = True)
    
    def createBook(self, rootDir):
        if self.titlePage:
            self.__makeTitlePage()
        if self.tocPage:
            self.__makeTocPage()
        self.rootDir = rootDir
        self.makeDirs()
        self.__writeMimeType()
        self.__writeItems()
        self.__writeContainerXML()
        self.__writeContentOPF()
        self.__writeTocNCX()


def test():
    def getMinimalHtml(text):
        return """<!DOCTYPE html PUBLIC "-//W3C//DTD XHtml 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>%s</title></head>
<body><p>%s</p></body>
</html>
""" % (text, text)

    book = EpubBook()
    book.setTitle('Most Wanted Tips for Aspiring Young Pirates')
    book.addCreator('Monkey D Luffy')
    book.addCreator('Guybrush Threepwood')
    book.addMeta('contributor', 'Smalltalk80', role = 'bkp')
    book.addMeta('date', '2010', event = 'publication')
    
    book.addTitlePage()
    book.addTocPage()
    book.addCover(r'D:\epub\blank.png')
    
    book.addCss(r'main.css', 'main.css')

    n1 = book.addHtml('', '1.html', getMinimalHtml('Chapter 1'))
    n11 = book.addHtml('', '2.html', getMinimalHtml('Section 1.1'))
    n111 = book.addHtml('', '3.html', getMinimalHtml('Subsection 1.1.1'))
    n12 = book.addHtml('', '4.html', getMinimalHtml('Section 1.2'))
    n2 = book.addHtml('', '5.html', getMinimalHtml('Chapter 2'))

    book.addSpineItem(n1)
    book.addSpineItem(n11)
    book.addSpineItem(n111)
    book.addSpineItem(n12)
    book.addSpineItem(n2)

    # You can use both forms to add TOC map
    #t1 = book.addTocMapNode(n1.destPath, '1')
    #t11 = book.addTocMapNode(n11.destPath, '1.1', parent = t1)
    #t111 = book.addTocMapNode(n111.destPath, '1.1.1', parent = t11)
    #t12 = book.addTocMapNode(n12.destPath, '1.2', parent = t1)
    #t2 = book.addTocMapNode(n2.destPath, '2')
    
    book.addTocMapNode(n1.destPath, '1')
    book.addTocMapNode(n11.destPath, '1.1', 2)
    book.addTocMapNode(n111.destPath, '1.1.1', 3)
    book.addTocMapNode(n12.destPath, '1.2', 2)
    book.addTocMapNode(n2.destPath, '2')

    rootDir = r'c:\temp\test'
    book.createBook(rootDir)
    EpubBook.createArchive(rootDir, rootDir + '.epub')
    EpubBook.checkEpub('epubcheck-1.0.5.jar', rootDir + '.epub')
    
if __name__ == '__main__':
    test()
