#!/usr/bin/env python
# Necessary modules
import scholarly as sc           # Version from https://github.com/cnettlev/scholarly
from habanero import Crossref
import unicodecsv as csv
from collections import OrderedDict
from string import punctuation
from difflib import SequenceMatcher
# Retrieving command-line arguments
from searchCitations_Options import options

MAX_CHAR = 100 # Maximum characters to be compared as title (for too long titles scholar might use ...)
MAX_SCHO = 5   # Maximum entries to check with searched item

## For completing data using Crossref API habanero
cr = Crossref()

## Utilities for fixing syntaxis
tr_table = dict((ord(c), None) for c in (set(punctuation)))
def cleanTitle(title,tr=tr_table):
    title = title.lower()
    if type(title) == str:
        return title.translate(None,punctuation).replace(' ','')
    else:
        return title.translate(tr).replace(' ','')

def reprintCrossReffAuthors(authors):
    out = ''
    for it in range(len(authors)):
        given = authors[it].get('given','')
        if given:
            out += given + ' ' + authors[it].get('family','')
        else:
            out += authors[it].get('family','')
        if it < len(authors)-1:
            out +=', '
    return out

def compareTitles(title1,title2,opt=options.matcher):
    if opt < 1:
        return SequenceMatcher(None, title1, title2).ratio() > opt
    else:
        return title1==title2

## Dictionary item
dItem = OrderedDict([('Title',''),('Author',''),('Source title',''),('Publisher',''),('Document Type',''),('DOI',''),('Volume',''),('Issue','')])

def addItem(wtr,title,authors='',name='',pub='',type='',doi='',vol='',issue=''):
    dItem['Title']         = title
    dItem['Author']        = authors
    dItem['Source title']  = name
    dItem['Publisher']     = pub
    dItem['Document Type'] = type
    dItem['DOI']           = doi
    dItem['Volume']        = vol
    dItem['Issue']         = issue

    dict_writer.writerow(dItem)

def searchAndAppend(title,querier,writer,lastTry='',tryAgain=True):
    print 'Searching for',title
    ## Searching into scholar
    scholarSearch = querier.search_pubs_query(title)
    scholarFound = False

    for i in range(MAX_SCHO):
        paper = next(scholarSearch,None)
        if paper is None:
            break
        print "Scholar ("+str(i)+'/'+str(MAX_SCHO)+'):',paper.bib['title']

        if lastTry:
            title = title.replace(' '+lastTry,'')

        if compareTitles(cleanTitle(title)[0:MAX_CHAR], cleanTitle(paper.bib['title'])[0:MAX_CHAR]):
            scholarFound = True
            print 'Found: ',paper.bib['title']
            print 'Authors:',paper.bib['author']
            print 'Cited by:',paper.citedby

            if paper.citedby:
                ## Searching citations to article
                print
                print 'Searching cited by'
                cb = paper.get_citedby()
                count = 0

                print
                for citation in cb:
                    bibItem = citation.bib
                    count += 1
                    print '\tArticle('+str(count)+'/'+str(paper.citedby)+')\t',bibItem['title']
                    print '\tAuthors\t\t',bibItem['author']
                    print '\tVolume\t\t',bibItem['volume']
                    print '\tPublisher\t',bibItem['publisher']

                    cit_cleanTitle = cleanTitle(bibItem['title'].encode("ascii","ignore"))[0:MAX_CHAR]
                    crSearch = cr.works(query_title=bibItem['title']+' '+bibItem['author'],sort='score',limit=5)
                    found = False

                    for z in crSearch['message']['items']:
                        print '\tCrossref item:\t',z['title'][0]
                        if compareTitles(cit_cleanTitle, cleanTitle(z['title'][0].encode("ascii","ignore"))[0:MAX_CHAR]):
                            print '\tDOI:\t\t',z['DOI']
                            print '\tSubject:\t',z.get('subject')

                            found = True
                            authorData = reprintCrossReffAuthors(z.get('author',''))
                            if not authorData:
                                authorData = bibItem['author']
                            cTitle = z.get('container-title','')
                            if cTitle:
                                cTitle = cTitle[0]
                            addItem(writer,z.get('title')[0],authorData,cTitle,
                                z.get('publisher',''),z.get('type',''),z.get('DOI',''),
                                z.get('volume',''),z.get('issue',''))
                            break

                    if not found:
                        print '\t*** Unable to find title in Crossref! ***'

                        addItem(writer,bibItem['title'],bibItem['author'],pub=bibItem['publisher'],type='other')

                    print
            break
    if not scholarFound and tryAgain:
        print 'Not found!!'
        if lastTry:
            searchAndAppend(title+' '+lastTry,querier,writer,lastTry,False)


## Writing results in CSV
with open(options.outFile,'wb') as output_file:
    dict_writer = csv.DictWriter(output_file, dItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
    dict_writer.writeheader()

    scQuerier = sc.querier('search_cookies.tmp')

    ## Reading input CSV
    if options.inFile:
        with open(options.inFile) as csvfile:
            reader = csv.DictReader(csvfile,delimiter=options.inDelimiter)
            nArticles = len(list(reader))
            csvfile.seek(0)
            reader.__init__(csvfile, delimiter=options.inDelimiter)
            cArticle = 1
            for row in reader:
                print "\nArticle",cArticle,"of",nArticles
                cArticle += 1
                ## Searching title in google scholar
                title = row.get('Title','') # 'The interaction of maturational constraints and intrinsic motivations in active motor development'
                if not title:
                    title = row.get('Article Title','')
                if not title:
                    print 'Error with CSV identifier. It must contain either Title or Article Title'
                    exit()
                if options.lastTry:
                    lt = ''
                    if options.lastTry is not None:
                        lt = row.get(options.lastTry,'')
                        if not lt:
                            lt = options.lastTry
                    searchAndAppend(title,scQuerier,dict_writer,lt)
                else:
                    searchAndAppend(title,scQuerier,dict_writer)
    else:
        searchAndAppend(options.title,scQuerier,dict_writer,options.lastTry)

# ## Writing results in CSV
# if len(articlesDict):
#   with open(options.outFile,'wb') as output_file:
#       dict_writer = csv.DictWriter(output_file, articlesDict[0].keys(),encoding='utf-8',delimiter=options.outDelimiter)
#       dict_writer.writeheader()
#       dict_writer.writerows(articlesDict)
