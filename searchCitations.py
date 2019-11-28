#!/usr/bin/env python
# Necessary modules
import scholarly as sc           # Version from https://github.com/cnettlev/scholarly
from habanero import Crossref
import unicodecsv as csv
from collections import OrderedDict
from string import punctuation
from difflib import SequenceMatcher
from os import path, rename, getcwd
import sys

try:
    sys.path.insert(1, getcwd()+'../csv-articles/src/')
    import reformat
except ImportError:
    reformat = None 

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
dItem = OrderedDict([('No. Citation',''),('Title',''),('First Author',''),('Authors',''),('Container',''),('Publisher',''),('Document Type',''),('DOI',''),('Volume',''),('Issue',''),('No. Article','')])
rItem = OrderedDict([('Title',''),('Author',''),('Cited by','')])

def addItem(wtr,nCitation,title,authors='',container='',pub='',type='',doi='',vol='',issue='',nCitedArticle=0):
    if reformat:
        reformat.reformatAuthors(authors)

    dItem['No. Citation']  = nCitation
    dItem['Title']         = title
    dItem['First Author']  = authors.split(',')[0]
    dItem['Authors']       = authors
    dItem['Container']     = container
    dItem['Publisher']     = pub
    dItem['Document Type'] = type
    dItem['DOI']           = doi
    dItem['Volume']        = vol
    dItem['Issue']         = issue
    dItem['No. Article']   = nCitedArticle

    wtr.writerow(dItem)

def addItemResumee(wtr,title,author,citations):
    rItem['Title']         = title
    rItem['Author']        = author
    rItem['Cited by']      = citations

    wtr.writerow(rItem)

def searchAndAppend(nArticle,title,querier,writer,writer_r='',lastTry='',tryAgain=True):
    if len(title) == 2:
        author = title[1]
        title = title[0]
    else:
        author = ''

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
            
            if writer_r:
                # print "Adding writter"
                addItemResumee(writer_r,title,author,paper.citedby)

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
                    crSearch = cr.works(query=bibItem['title']+' '+bibItem['author'],limit=5)
                    found = False

                    for z in crSearch['message']['items']:
                        crTitle = z.get('title','')
                        if crTitle:
                            crTitle = crTitle[0]
                            print '\tCrossref item:\t',crTitle
                            if compareTitles(cit_cleanTitle, cleanTitle(crTitle.encode("ascii","ignore"))[0:MAX_CHAR]):
                                print '\tDOI:\t\t',z['DOI']
                                print '\tSubject:\t',z.get('subject')

                                found = True
                                authorData = reprintCrossReffAuthors(z.get('author',''))
                                if not authorData:
                                    authorData = bibItem['author']

                                cTitle = z.get('container-title','')
                                if cTitle:
                                    cTitle = cTitle[0]

                                addItem(writer,count-1,z.get('title')[0],authors=authorData,container=cTitle,
                                    pub=z.get('publisher',''),type=z.get('type',''),doi=z.get('DOI',''),
                                    vol=z.get('volume',''),issue=z.get('issue',''),nCitedArticle=nArticle)
                                break

                    if not found:
                        print '\t*** Unable to find title in Crossref! ***'

                        addItem(writer,count-1,bibItem['title'],authors=bibItem['author'],pub=bibItem['publisher'],type='other',nCitedArticle=nArticle)

                    print
            break
    if not scholarFound and tryAgain:
        print 'Not found!!'
        if lastTry:
            searchAndAppend(nArticle,title+' '+lastTry,querier,writer,writer_r,lastTry,False)

def start_from_previous_work():
    # Check, clean and retreive information about existing data
    if path.exists(options.resumee):
        with open(options.resumee) as resumee:
            reader = csv.DictReader(resumee,delimiter=options.outDelimiter)
            nArticles = len(list(reader))
            resumee.seek(0)
            reader.__init__(resumee, delimiter=options.outDelimiter)
            cArticle = 1
            citations = 0

            new_resumee = open(options.resumee+'2','wb')
            other = csv.DictWriter(new_resumee, rItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
            other.writeheader()

            print "previous: ",nArticles
            for row in reader:
                print row.get('Title',''),row.get('Cited by','')
                if cArticle < nArticles:
                    citations += float(row.get('Cited by',''))
                    addItemResumee(other,row.get('Title',''),row.get('Author',''),row.get('Cited by',''))
                cArticle += 1

        rename(options.resumee+'2',options.resumee)

        return [cArticle,citations]
    return [0,0]


pArticles, pCitations = start_from_previous_work()
alreadyHere = path.exists(options.outFile)
openWith = 'a'

if alreadyHere:
    print "Output file "+options.outFile+" already exists. Trying to continue there..."
    with open(options.outFile) as output_file:
        reader = csv.DictReader(output_file,delimiter=options.outDelimiter)
        nArticles = len(list(reader))
        if pCitations != nArticles: # inconsistent data from previous processing
            openWith = 'wb'
            alreadyHere = False

## Writing results in CSV
with open(options.outFile,openWith) as output_file:
    
    dict_writer = csv.DictWriter(output_file, dItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
    if not alreadyHere:
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
            if options.resumee:
                resumee = open(options.resumee,openWith)
                dict_writer_r = csv.DictWriter(resumee, rItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
                if not alreadyHere:
                    dict_writer_r.writeheader()
            else:
                dict_writer_r = ''
            for row in reader:
                print "\nArticle",cArticle,"of",nArticles

                if cArticle < pArticles:
                    cArticle += 1
                    continue
                elif cArticle-1 != int(row.get('','-1')):
                    print cArticle-1, int(row.get('','-1'))
                    print 'Error: article number inconsistent with the one from input CSV.'
                    exit()

                ## Searching title in google scholar
                title = row.get('Title','') # 'The interaction of maturational constraints and intrinsic motivations in active motor development'

                if not title:
                    title = row.get('Article Title','')
                if not title:
                    print 'Error with CSV identifier. It must contain either Title or Article Title'
                    exit()

                if options.resumee:
                    author = row.get('Authors','')
                    title = (title,author)

                if options.lastTry:
                    lt = ''
                    if options.lastTry is not None:
                        lt = row.get(options.lastTry,'')
                        if not lt:
                            lt = options.lastTry
                    searchAndAppend(cArticle-1,title,scQuerier,dict_writer,dict_writer_r,lt)
                else:
                    searchAndAppend(cArticle-1,title,scQuerier,dict_writer,dict_writer_r)

                cArticle += 1
        if options.resumee:
            resumee.close()
    else:
        searchAndAppend(0,options.title,scQuerier,dict_writer,lastTry=options.lastTry)

# ## Writing results in CSV
# if len(articlesDict):
#   with open(options.outFile,'wb') as output_file:
#       dict_writer = csv.DictWriter(output_file, articlesDict[0].keys(),encoding='utf-8',delimiter=options.outDelimiter)
#       dict_writer.writeheader()
#       dict_writer.writerows(articlesDict)
