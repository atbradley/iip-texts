import configparser
import csv
from pathlib import Path

from lxml import etree


config = configparser.ConfigParser()
config.read("iip_toolkit.ini")

HERE = Path(__file__).parent
INPATH = HERE / config["word_lists"]["infile_path"]
OUTPATH = HERE / config["word_lists"]["outfile_path"]

# Read all segmented files for processing word lists
vSegmentedTexts = glob.glob(strPathOut + os.sep + '*.xml')
vSegmentedTexts.sort()

WORD_LISTS = {}
WORD_COUNT = 0

# Loop through texts building lists
for strSegmentedTextFullPath in vSegmentedTexts:

	# Extract the filename for the current text
	# Use the OS specific directory separator to split path and take the last element
	strTextFilename = strSegmentedTextFullPath.split(os.sep)[-1]

	# Current parser options clean up redundant namespace declarations and remove patches of whitespace
	# For more info, see "Parser Options" in: https://lxml.de/parsing.html
	parser = etree.XMLParser(ns_clean=True, remove_blank_text=False)
	try:
		xmlText = etree.parse(strSegmentedTextFullPath, parser)
	except Exception as e:

		print('#' * 20)
		print('Error with building lists for XML:')
		print(e)
		print(strSegmentedTextFullPath)
		print('#' * 20)
		continue

	wordElems = xmlText.findall(".//tei:div[@type='edition'][@subtype='transcription_segmented']/tei:p/tei:w", namespaces=nsmap)
	WORD_COUNT += len(wordElems)

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

			if wordElem.attrib[XML_NS + 'lang'] in WORD_LISTS:
				WORD_LISTS[wordElem.attrib[XML_NS + 'lang']].append([text, wordNumber, normalized, wordElem.attrib[XML_NS + 'lang'], wordIsNum, wordElemText])
			else:
				WORD_LISTS[wordElem.attrib[XML_NS + 'lang']] = [[text, wordNumber, normalized, wordElem.attrib[XML_NS + 'lang'], wordIsNum, wordElemText]]



# Write word lists to CSV files
# for lang in WORD_LISTS:
#
# 	# write to file
# 	with open(strPathListOut + '/word_list_{}.csv'.format(lang.lower()), 'w') as csvfile:
# 		csvwriter = csv.writer(csvfile)
# 		for word_row in WORD_LISTS[lang]:
# 			csvwriter.writerow(word_row)

print("#" * 20)
print("#" * 20)
print("Total word count:")
print(WORD_COUNT)
print("Transformation errors:")
print(transformationErrors)
print("#" * 20)
