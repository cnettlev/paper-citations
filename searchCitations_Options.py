from optparse import OptionParser
import os

usage = "Usage: \n\t%prog -i INPUT_CSV [OPTIONS]\n\n\tor\n\n\t%prog -t ARTICLE_TITLE [OPTIONS]"
parser = OptionParser(usage=usage)
parser.add_option("-d", "--delimiter", dest="delimiter", default=',',
                  help="(Optional) Delimiter to be use with both, INPUT_CSV and OUTPUT_CSV. To use \\t or other similar special characters in bash use $\'\\t\'. [default: %default]", metavar="DEL")
parser.add_option("--delimiter-input", dest="inDelimiter", default='',
                  help="(Optional) Delimiter to be use with INPUT_CSV. Overwrites -d DELIMITER option.", metavar="iDEL")
parser.add_option("--delimiter-output", dest="outDelimiter", default='',
                  help="(Optional) Delimiter to be use with OUTPUT_CSV. Overwrites -d DELIMITER option.", metavar="oDEL")
parser.add_option("-e", "--email", dest="email", default='',
                  help="Email used while querying to crossref. Using an email enables to query being assigned to their \"polite pool\".", metavar="CR_EMAIL")
parser.add_option("-i", "--input", dest="inFile", default='',
                  help="Name of the CSV file containing a list of articles to get citations for. This file must contain a data identifier named \"Title\" or \"Article Title\".", metavar="INPUT_CSV")
parser.add_option("-l", "--lastTry", dest="lastTry", default=None,
                  help="(Optional) If INPUT_CSV is given, another identified named as LAST_TRY is appended to a title if the title alone is not enough for finding the article. If there is no identifier in the CSV file or ARTICLE_TITLE is given, LAST_TRY is appended to the title.", metavar="LAST_TRY")
parser.add_option("-m", "--match-percent", dest="matcher", type="float", default=1,
                  help="When titles are compared, a matching percentage can be use, to avoid hard exact comparitons. [default: %default]", metavar="MATCH")
parser.add_option("-n", "--not-found", dest="saveNotFound", action="store_true", default=False,
                  help="Flag that enables the storing a not-found.csv file containing a resummee of the articles already searched for but that weren't found. [default: %default]", metavar="MATCH")
parser.add_option("-o", "--output", dest="outFile", default='',
                  help="(Optional) Name of the output CSV file containing the articles citing the list from INPUT_CSV. By default, the file uses the INPUT_CSV name as \"cit_INPUT_CSV\" or, similarly, the ARTICLE_TITLE.", metavar="OUTPUT_CSV")
parser.add_option("-p", "--proxy", dest="proxy", default='',
                  help="(Optional) Enables the use of a proxy for gscholar requests.", metavar="PROXY")
parser.add_option("-r", "--resumeeFolder", dest="resumeeFolder", default='./',
                  help="(Optional) Name of a folder to be used for validation. This folder is created if necessary. [default: %default]", metavar="VALIDATION_FOLDER")
parser.add_option("-t", "--title", dest="title", default='',
                  help="Instead of a CSV file, a single title can be used for searching citing articles.", metavar="ARTICLE_TITLE")

(options, args) = parser.parse_args()

if not options.inFile and not options.title:
	print "Usage error!!!\n"
	parser.print_help()
	exit()

options.resumeeFolder = options.resumeeFolder.rstrip('/')
if not os.path.exists(options.resumeeFolder):
    os.makedirs(options.resumeeFolder)

[inFolder,inFile] = os.path.split(options.inFile)
[outFolder,outFile] = os.path.split(options.outFile)

if not options.outFile:
	if options.inFile:
		options.outFile = inFolder + 'cit_' + inFile
		options.resumee = options.resumeeFolder+'/cit_r_' + inFile
	else:
		options.outFile = 'cit_' + options.title + '.csv'
		options.resumee = ''
else:
	options.resumee = options.resumeeFolder+'/r-' + outFile

if not options.inDelimiter:
	options.inDelimiter = options.delimiter
if not options.outDelimiter:
	options.outDelimiter = options.delimiter
