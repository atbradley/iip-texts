#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Segment words from the XML files with <w> elements.

DISCLAIMER - this is a prototype and not meant to be used in production

"""

import configparser
import logging
import os
from pathlib import Path
import re
import copy
from lxml import etree


# Local dependencies
from argument_parser import *

config = configparser.ConfigParser()
config.read("iip_toolkit.ini")

loglevel: int = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger("iip_toolkit")
log.setLevel(loglevel)


#Current location, input and output paths.
#TODO: Here should be the main script's directory. Or use Path.home() as the anchor.
HERE: Path = Path(__file__).parent
INPATH: Path = HERE / config["word_segmentation"]["infile_path"]
OUTPATH: Path = HERE / config["word_segmentation"]["outfile_path"]

#Make sure outpath exists.
if not OUTPATH.exists():
	OUTPATH.mkdir()

# Get a list of all texts for processing
# Use command line arguments of the form "file1, file2, file3, etc." when given
# Otherwise, just use all files in the input directory
filenames = ParseArguments()
if filenames is None:
	infiles = INPATH.glob('*.xml')
else:
	infiles = [INPATH / strFilename for strFilename in vFilenames]

infiles = sorted(infiles)

strTextsAll = ""
strExtraCharacters = ""

vNoLang = []
vLangs = []
vFoobarred = []

vAllowedLangs = [ 'arc', 'grc', 'he', 'la', 'x-unknown', 'syc', 'phn', 'xcl', 'Other', 'geo']
transformationErrors: int = 0




# Loop through the list of texts, parse XML, make data frames, save as CSV
for infile in infiles:

	# bypass the xxx inscriptions
	if "xxx" in str(infile):
		continue

	# Extract the filename for the current text
	# Use the OS specific directory separator to split path and take the last element
	infilename = infile.name

	# Current parser options clean up redundant namespace declarations and remove patches of whitespace
	# For more info, see "Parser Options" in: https://lxml.de/parsing.html
	parser = etree.XMLParser(ns_clean=True, remove_blank_text=False)

	try:
		xmlText = etree.parse(str(infile), parser)
	except Exception as e:
		logging.warn(f'Error with parsing {infilename} text as XML: {e}')
		transformationErrors += 1
		continue

	#ns = {'tei': "http://www.tei-c.org/ns/1.0"}
	TEI_NS = "http://www.tei-c.org/ns/1.0"
	XML_NS = "{http://www.w3.org/XML/1998/namespace}"
	nsmap = {
		'tei': TEI_NS,
	}
	TEI_NS = "{%s}" % TEI_NS

	textLang = xmlText.find('.//' + TEI_NS + 'textLang')

	# Get text-wide language settings
	strMainLanguage = ''
	try:
		strMainLanguage = textLang.attrib['mainLang']
	except:
		vNoLang.append(infilename)
		strMainLanguage = 'grc'
		continue

	# Find cases where language code is wrong
	if strMainLanguage not in vAllowedLangs:
		logging.warn("Error, invalid language (%s) in %s" % (strMainLanguage, infilename))
		continue


	vLangs.append(strMainLanguage)

	try:
		strOtherLanguages = textLang.attrib['otherLangs'].strip()
		if(len(strOtherLanguages) < 2):
			strOtherLanguages = None

	except:
		strOtherLanguages = None

    # test to see if there is a transcription div ?

	#Get a list of all paragraphs in transcription.
	paragraphs = xmlText.findall(".//tei:div[@type='edition'][@subtype='transcription']//tei:p", namespaces=nsmap)

	# Skip it if the text has no textual content,
	if len(paragraphs) < 1:
		logging.error('No content ' + infilename)
		vFoobarred.append(infilename)
		continue
		# this should copy the file without changing it.

	#Create a new element to store segmented data.
	body = xmlText.find(".//tei:body", namespaces=nsmap)
	transcription = xmlText.find(".//tei:div[@type='edition'][@subtype='transcription']", namespaces=nsmap)
	transcriptionSegmented = copy.deepcopy(transcription)
	transcriptionSegmented.clear()
	transcriptionSegmented.attrib['type'] = "edition"
	transcriptionSegmented.attrib['subtype'] = "transcription_segmented"

	for para in paragraphs:
		# Get script/language from attribute on <p> when it exists
		# Right now this is unused, according to TEI, defines script (which is already obvious)
		if XML_NS + 'lang' in para.attrib:
			strPLanguage = para.attrib[XML_NS + 'lang']

		try:
			words = []
			editionSegmented = copy.deepcopy(para)
			editionSegmented.clear()

			strXMLText = etree.tostring(para, encoding='utf8', method='xml').decode('utf-8')

			# add test for empty strXMLText and don't process if it's emtpy
			if not strXMLText or not len(strXMLText):
				continue

			# remove all <lb>s
			strXMLText = re.sub(r"<lb break=\"no\"(\s*)/>", "", strXMLText)
			strXMLText = re.sub(r"(\s*)<lb break=\"no\"(\s*)/>(\s*)", "", strXMLText)
			strXMLText = re.sub(r"<lb\s*/>", " ", strXMLText)

			# Just delete <note>...</note> right from the start. Shouldn't be there anyway.
			strXMLText = re.sub(r"<note>([^<]*?)</note>", "", strXMLText)

			# Discard a bunch of stuff that we don't really care about in this context
			strXMLText = re.sub(r"<([/]*)gap([/]*)>", " ", strXMLText)
			strXMLText = re.sub(r"<([/]*)gap ([^>]*?)>", " ", strXMLText)
			strXMLText = re.sub(r"<orgName>(.*?)</orgName>", "", strXMLText)
			strXMLText = re.sub(r"<([/]*)handShift([^>]*?)>", " ", strXMLText)
			strXMLText = re.sub(r"<space([^>]*?)>", " ", strXMLText)

			# replace every space inside pointy brackets with a bullet
			# make the w breaks
			# take every space and make it into a w
			# add begin w and end w
			# put back the spaces

			# Convert any amount of whitespace to a single space
			strXMLText = " ".join(strXMLText.split())

			# Convert all spaces within element tag definitions (<>) to bullets
			# Run multiple times to get all the spaces between attribute names
			# EM has tried to remove all newlines from start tags.
			# EM checked and we don't seem to have elements with more than three
			# attributes inside <p>.
			# EM has checked and there don't seem to be multivalued attributes in <p>
			strXMLText = re.sub(r"<(\w+)\s([^>]*)>", "<\\1•\\2>", strXMLText)
			strXMLText = re.sub(r"<([^>]*)\s([^>]*)>", "<\\1•\\2>", strXMLText)
			strXMLText = re.sub(r"<([^>]*)\s([^>]*)>", "<\\1•\\2>", strXMLText)

			#convert all spaces within element content in numbers to bullets as
			# well.
			# strXMLText = re.sub(r"<(num[^>]*>[^\s]+)\s+", "<\\1•", strXMLText)

			# Convert all whitespace in document to <w>s
			strXMLText = re.sub(r"\s+", "</w> <w>", strXMLText)

			# Add a start and end <w>
			strXMLText = re.sub(r'<p([^>]*[^/])>', '<p\\1><w>', strXMLText)
			strXMLText = re.sub(r"</p>", "</w></p>", strXMLText)

			# remove any empty ws
			strXMLText = re.sub(r"<w></w>", "", strXMLText)

			#remove <w>s that only contain punctuation
			strXMLText = re.sub(r"<w[^>]+>[.,]</w>", "", strXMLText)

			#remove <w> elements that contain only a <g> element.
			strXMLText = re.sub(r"<w><g[^/]+/></w>", "", strXMLText)
			strXMLText = re.sub(r"<w><[^>]+><g[^/]+/></[^>]+></w>", "", strXMLText)
			strXMLText = re.sub(r"<w><g[^>]+>[^<]+</g></w>", "", strXMLText)
			strXMLText = re.sub(r"<w><[^>]+><g[^>]+>[^<]+</g></[^>]+></w>", "", strXMLText)

			# Convert the bullets back to spaces
			strXMLText = strXMLText.replace("•", " ")

			logging.debug(strXMLText)

			strXMLText = re.sub(r"§+", "§", strXMLText)
			strXMLText = re.sub(r"§", " ", strXMLText)

			editionSegmented = etree.XML(strXMLText, parser)	
			editionSegmented.tail = "\n"
			transcriptionSegmented.append(editionSegmented)
			transcriptionSegmented.tail = "\n"

			logging.debug(f"Done parsing {infile.name} as XML")
		except Exception as e:
			logging.error(f'Error with parsing edition {infile.name} as XML: {e}')
			logging.error(f'Modified XML: {strXMLText}')
			transformationErrors += 1
			continue

		body.append(transcriptionSegmented)



	# In a separate script now.
	if False:
		## all child nodes should have ids
		wordElems = editionSegmented.findall(".//tei:w", namespaces=nsmap)
		for i, wordElem in enumerate(wordElems):
			wordElem.attrib[XML_NS + 'id'] = '{}-{}'.format(os.path.splitext(infilename)[0], i + 1)
			has_foreign_elem = False
			for child in wordElem:
				if child.tag == '{http://www.tei-c.org/ns/1.0}supplied' and XML_NS + 'lang' in child.attrib:
					wordElem.attrib[XML_NS + 'lang'] = child.attrib[XML_NS + 'lang']
					has_foreign_elem = True
			if not has_foreign_elem:
				wordElem.attrib[XML_NS + 'lang'] = strMainLanguage


	xmlData = etree.tostring(xmlText, encoding='utf-8', pretty_print=False, xml_declaration=True)

	with (OUTPATH / infile.name).open('wb') as file:
		file.write(xmlData)

	# strXMLText = re.sub(r"<lb break=\"no\"(\s*)/>", "¶", strXMLText)
