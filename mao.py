# -*- coding: utf-8 -*-

import re
import ez_epub
import os
from operator import itemgetter, attrgetter

gImgNumber = 1

def getFileList(folder): #(fileName, fileNameWithPath, number, '-')
	
	def splitName(name):
		words = re.split(r' |\.',name)
		return [int(words[0]), words[1]]
		
	fileList = []
	for root, subFolders, files in os.walk(folder):
		for file in files:
			file_dir_path = os.path.join(root,file)
			p = splitName(file)
			fileList.append((file,file_dir_path,p[0],p[1]))

	fileList.sort(key=lambda x: (x[2],x[3]=='-'))

	return fileList
	
def makeSectionWithImage(title,text,path):
	global gImgNumber
	section = ez_epub.Section()
	section.title = title
	section.templateFileName = 'ez-section-img.xhtml'
	section.withImg = True
	
	items = []
	item = {}
	flag = ''
	
	paragraphs = text.strip().split('\n')
	tag_img = re.compile(r'<img>[0-9]+</img>')
	tag_number = re.compile(r'[0-9]+')

	for paragraph in paragraphs:
	
		if(flag == 'tag_img'):
			flag = ''
			
			result = tag_img.match(paragraph)
			
			if(result):
				item['comment'] = ''
				items.append(item)
				item = {}
				
				flag = 'tag_img'
				group = result.group()
				#print(group)
				result2 = tag_number.search(group)
				number = result2.group()
				item['img_src'] = path + "\\" + title + "\\" + number + ".jpg"
				#item['img_dst'] = 'img' + str(gImgNumber) + '_' + number + ".jpg"
				item['img_dst'] = title + '_' + number + ".jpg"
			else:
				item['comment'] = paragraph
				#item['comment'] = paragraph.encode('utf-8')
				items.append(item)
				item = {}
			
		else:
			result = tag_img.match(paragraph)
			
			if(result):
				flag = 'tag_img'
				group = result.group()
				#print(group)
				result2 = tag_number.search(group)
				number = result2.group()
				item['img_src'] = path + "\\" + title + "\\" + number + ".jpg"
				#item['img_dst'] = 'img' + str(gImgNumber) + '_' + number + ".jpg"
				item['img_dst'] = title + '_' + number + ".jpg"
			else:
				items.append(paragraph)
				#items.append(paragraph.encode('utf-8'))
		
	if(flag == 'tag_img'):
		item['comment'] = ''
		items.append(item)
		item = {}
			
	print(items)
	section.text = items
	gImgNumber = gImgNumber + 1
	return section

def makeSectionWithoutImage(title,text):	
			
	section = ez_epub.Section()
	section.css = """.em { font-style: italic; }"""
	section.title = title
	#section.title = title.encode('utf-8')
	
	#add list of paragraph into section.text
	paragraphs = text.strip().split('\n')
	section.text = paragraphs
	#for p in paragraphs:
	#	section.text.append(p.encode('utf-8'))
		
	return section
	
def isImgSection(fileName):
	words = re.split(r' |\.',fileName)
	if(words[1] == '-'):
		return True
	else:
		return False
	
def makeSections(fileList):

	path = os.getcwd() + r'\..\..\破解文革毛泽东(txt版)\images'
	sections = []
	
	for file in fileList:
	
		print(file[0])
	
		content_file=open(file[1], mode='r', encoding='gbk', errors='strict') 
		content = content_file.read()
		content_file.close()
		
		title = file[0].partition('.')[0]	
		
		if(isImgSection(file[0])):
		
			print(file[0] + ' is img section')
			
			section = makeSectionWithImage(title,content,path)
			sections.append(section)
				
		else:
			section = makeSectionWithoutImage(title,content)
			sections.append(section)
		
	return sections
	
if __name__ == '__main__':
	path = os.getcwd()
	path = path + r'\..\..\破解文革毛泽东(txt版)\text'
	textFileList = getFileList(path)
	book = ez_epub.Book()
	book.title = '破解文革毛泽东'
	book.authors = ['崇新越','百思峰']
	book.cover = path + r'\..\..\破解文革毛泽东(txt版)\cover.jpg'
	book.sections = makeSections(textFileList)
	book.make(r'C:\Temp\%s' % book.title)
	