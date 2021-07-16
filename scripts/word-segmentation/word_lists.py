from collections import defaultdict
import configparser
import csv
import logging
from pathlib import Path

from lxml import etree


# Local dependencies
from argument_parser import *

config = configparser.ConfigParser()
config.read("iip_toolkit.ini")

loglevel: int = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger("iip_toolkit")
log.setLevel(loglevel)

config = configparser.ConfigParser()
config.read("iip_toolkit.ini")

HERE = Path(__file__).parent
INPATH = HERE / config["word_lists"]["infile_path"]
OUTPATH = HERE / config["word_lists"]["outfile_path"]

#Make sure outpath exists.
if not OUTPATH.exists():
	OUTPATH.mkdir()


#ns = {'tei': "http://www.tei-c.org/ns/1.0"}
TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "{http://www.w3.org/XML/1998/namespace}"
NSMAP = {
	'tei': TEI_NS,
}
TEI_NS = "{%s}" % TEI_NS

# Loop through texts building lists
def build_word_lists(infiles) -> bool:
	word_count = 0
	word_lists = defaultdict(list)
	for infile in infiles:
		# Extract the filename for the current text
		strTextFilename = infile.name

		# Current parser options clean up redundant namespace declarations and remove patches of whitespace
		# For more info, see "Parser Options" in: https://lxml.de/parsing.html
		parser = etree.XMLParser(ns_clean=True, remove_blank_text=False)
		try:
			xmlText = etree.parse(str(infile), parser)
		except Exception as e:
			log.error('Error with building lists for XML (file: %s): %s', str(infile), e)
			continue

		wordElems = xmlText.findall(".//tei:div[@type='edition'][@subtype='transcription_segmented']/tei:p/tei:w", namespaces=NSMAP)
		word_count += len(wordElems)

		# Build word lists by language
		for wordElem in wordElems:
			# serialize the word elems to text
			wordElemText = etree.tostring(wordElem, encoding='utf8', method='xml').decode('utf-8').strip()
			wordElemText = wordElemText.replace('xmlns="http://www.tei-c.org/ns/1.0"', "")
			wordElemText = wordElemText.replace('xmlns:xi="http://www.w3.org/2001/XInclude"', "")

			# check if <num> elem is in text (quick method)
			wordIsNum = 0
			if "<num" in wordElemText:
				wordIsNum = 1

			# add version to unique/alphabetize on
			normalized = ''.join(wordElem.itertext()).strip()

			if wordElemText and len(wordElemText):
				wordParams = wordElem.attrib[XML_NS + 'id'].split('-')
				text = "{}.xml".format(wordParams[0])
				wordNumber = wordParams[1]
				lang = wordElem.attrib[XML_NS + 'lang']
				word_lists[lang].append([text, wordNumber, normalized, lang, wordIsNum, wordElemText])

	# Write word lists to CSV files
	for lang in word_lists:
		with (OUTPATH / f"{lang}.csv").open('w', encoding="utf8") as csvfile:
			csvwriter = csv.writer(csvfile)
			for word_row in word_lists[lang]:
				csvwriter.writerow(word_row)
	
	return True

	log.info("Total word count: %d", word_count)



if __name__ == "__main__":
	# Read all segmented files for processing word lists
	infiles = INPATH.glob('*.xml')
	infiles = sorted(infiles)
	build_word_lists(infiles)	
