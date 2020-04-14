#!/usr/bin/env python
# Necessary modules
import scholarly as sc           # Version from https://github.com/cnettlev/scholarly
from habanero import Crossref
import unicodecsv as csv
from collections import OrderedDict
from string import punctuation
from difflib import SequenceMatcher
import time
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
if options.email:
    Crossref(mailto=options.email)

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
rItem = OrderedDict([('No. Article',''),('Title',''),('Author',''),('Cited by',''),('Found','')])
sItem = dict([('title',''),('author',''),('year',''),('last-try','')])

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

def addItemResumee(wtr,nCitedArticle,title,author,citations,found=1):
    rItem['No. Article']   = nCitedArticle
    rItem['Title']         = title
    rItem['Author']        = author
    rItem['Cited by']      = citations
    rItem['Found']         = found

    wtr.writerow(rItem)

def searchAndAppend(search,querier,writer,writer_r='',tryAgain=True, previousWorked = False):
    global lastFromCrossref, working

    print 'Searching for',search['title']
    ## Searching into scholar
    if search['year']:
        scholarSearch = querier.search_pubs_query(search['title'],years=int(search['year']))
    else:
        scholarSearch = querier.search_pubs_query(search['title'])
    scholarFound = False
    scholarWorked = False

    for i in range(MAX_SCHO):
        paper = next(scholarSearch,None)
        scholarWorked |= (i == 0 and (paper is not None))
        if paper is None:
            break
        print "Scholar ("+str(i+1)+'/'+str(MAX_SCHO)+'):',paper.bib['title']

        if search['last-try']:
            search['title'] = search['title'].replace(' '+search['last-try'],'')

        if compareTitles(cleanTitle(search['title'])[0:MAX_CHAR], cleanTitle(paper.bib['title'])[0:MAX_CHAR]):
            fAuthor = paper.bib['author'].lower().split(',')[0]
            lastName = fAuthor.split(' ')
            if len(lastName)>1:
                lastName = lastName[1]
            initial = fAuthor[0]
            lastName2 = search['author'].lower().split(' ')[0]
            initial2 = search['author'].lower().split(' ')[1][0]

            if not compareTitles(lastName,lastName2) or not initial == initial2:
                print 'Unmatching authors:',paper.bib['author'],'('+initial+' '+lastName+')','('+initial2+' '+lastName2+')'
                sys.exit(0)
                continue
            scholarFound = True
            print 'Found: ',paper.bib['title']
            print 'Authors:',paper.bib['author'],'('+initial2+' '+lastName2+')'
            print 'Cited by:',paper.citedby
            
            if writer_r and lastFromCrossref == 0:
                # print "Adding writter"
                addItemResumee(writer_r,search['nArticle'],search['title'],search['author'],paper.citedby)

            if paper.citedby:
                ## Searching citations to article
                print
                print 'Searching cited by ('+str(lastFromCrossref)+')'
                cb = paper.get_citedby()
                count = 0

                print
                for citation in cb:
                    time.sleep(4*0.03)
                    if (count < lastFromCrossref):
                        count += 1
                        print str(count)+': '+citation.bib['title']
                        continue

                    bibItem = citation.bib

                    print '\tArticle('+str(count+1)+'/'+str(paper.citedby)+')\t',bibItem['title']
                    print '\tAuthors\t\t',bibItem['author']
                    print '\tVolume\t\t',bibItem['volume']
                    print '\tPublisher\t',bibItem['publisher']

                    cit_cleanTitle = cleanTitle(bibItem['title'].encode("ascii","ignore"))[0:MAX_CHAR]
                    crSearch = cr.works(query=bibItem['title']+' '+bibItem['author'],limit=10)
                    found = False

                    for z in crSearch['message']['items']:
                        crTitle = z.get('title','')
                        if crTitle:
                            crTitle = crTitle[0]
                            print '\tCrossref item:\t',crTitle
                            if compareTitles(cit_cleanTitle, cleanTitle(crTitle.encode("ascii","ignore"))[0:MAX_CHAR]):
                                lastName = bibItem['author'].lower().split(',')[0].split(' ')
                                if len(lastName)>1:
                                    lastName = lastName[1]

                                if z.get('author','') and z.get('author','')[0]['family'].lower() != lastName:
                                    print 'Unmatching authors:',lastName,'('+z.get('author','')[0]['family'].lower()+')'
                                    continue

                                print '\tDOI:\t\t',z['DOI']
                                print '\tSubject:\t',z.get('subject')

                                found = True
                                authorData = reprintCrossReffAuthors(z.get('author',''))
                                if not authorData:
                                    authorData = bibItem['author']

                                cTitle = z.get('container-title','')
                                if cTitle:
                                    cTitle = cTitle[0]

                                addItem(writer,count,z.get('title')[0],authors=authorData,container=cTitle,
                                    pub=z.get('publisher',''),type=z.get('type',''),doi=z.get('DOI',''),
                                    vol=z.get('volume',''),issue=z.get('issue',''),nCitedArticle=search['nArticle'])
                                break

                    if not found:
                        print '\t*** Unable to find title in Crossref! ***'

                        addItem(writer,count,bibItem['title'],authors=bibItem['author'],pub=bibItem['publisher'],type='other',nCitedArticle=search['nArticle'])

                    print
                    count += 1
                    lastFromCrossref = 0

                if count != paper.citedby:
                    print "\n\nError communicating with google-scholar.\nExiting...\n"
                    exit(1)
            break
        else:
            print 'Unmatching titles'
    if not scholarFound:
        print 'Not found!!'
        if tryAgain and search['last-try']:
            search['title'] = search['title']+' '+search['last-try']
            searchAndAppend(search,querier,writer,writer_r,False,scholarWorked)
        else:
            if search['last-try']:
                search['title'] = search['title'].replace(' '+search['last-try'],'')
            if previousWorked and not scholarWorked: 
            # try again to check if queries are working
                search['last-try'] = ''
                searchAndAppend(search,querier,writer,writer_r,False,scholarWorked)
            if scholarWorked:
                addItemResumee(writer_r,search['nArticle'],search['title'],search['author'],0,0)
            else:
                addItemResumee(writer_r,search['nArticle'],search['title'],search['author'],-1,0)
                working = False

def start_from_previous_work(saveNotFound=options.saveNotFound):
    # Check, clean and retreive information about existing data
    if path.exists(options.resumee):
        with open(options.resumee) as resumee, open(options.outFile) as output_file:
            output_reader = csv.DictReader(output_file,delimiter=options.outDelimiter)
            reader = csv.DictReader(resumee,delimiter=options.outDelimiter)
            nArticles = len(list(reader))
            resumee.seek(0)
            reader.__init__(resumee, delimiter=options.outDelimiter)
            cArticle = 0
            lastCitations = 0

            new_resumee = open(options.resumee+'2','wb')
            other = csv.DictWriter(new_resumee, rItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
            other.writeheader()

            if saveNotFound:
                nFound = open('notfound.csv','a')
                nfWriter = csv.DictWriter(nFound, rItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
                nfWriter.writeheader()

            print "previous: ",nArticles
            for row in reader:
                # print row.get('Title',''),row.get('Cited by','')
                expected = int(row.get('Cited by',''))
                rArticle = int(row.get('No. Article'))
                stored = 0
                # print "Stored/expected",stored,expected
                for cB in range(expected):
                    # print cB
                    try:
                        storedCitation = next(output_reader)
                        rArticle = int(storedCitation['No. Article'])
                        # print storedCitation
                        if int(storedCitation['No. Article']) == cArticle:
                            stored += 1
                            # print "Stored:",stored
                    except Exception as e:
                        # print e
                        break
                print "Stored/expected",stored,expected,"\t\t",rArticle,cArticle
                if saveNotFound and row.get('Found','')=='0':
                    addItemResumee(nfWriter,cArticle,row.get('Title',''),row.get('Author',''),row.get('Cited by',''),row.get('Found',''))
                if expected == -1:
                    break
                if stored > 0 or (stored == 0 and expected == 0):
                    addItemResumee(other,cArticle,row.get('Title',''),row.get('Author',''),row.get('Cited by',''),row.get('Found',''))
                if stored != expected:
                    lastCitations = stored
                    break
                cArticle += 1


        rename(options.resumee+'2',options.resumee)

        return [cArticle,lastCitations]
    return [0,0]


pArticles, lastFromCrossref = start_from_previous_work()
alreadyHere = path.exists(options.outFile)
openWith = 'a'
working = True

## Writing results in CSV
with open(options.outFile,openWith) as output_file:
    
    dict_writer = csv.DictWriter(output_file, dItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
    if not alreadyHere:
        dict_writer.writeheader()

    scQuerier = sc.querier(options.resumeeFolder+'/search_cookies.tmp')

    if options.proxy:
        scQuerier.set_proxy(options.proxy)

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

                if cArticle - 1 < pArticles:
                    cArticle += 1
                    continue
                elif cArticle-1 != int(row.get('','-1')):
                    print cArticle-1, int(row.get('','-1'))
                    print 'Error: article number inconsistent with the one from input CSV.'
                    exit()

                print "\nArticle",cArticle,"("+str(cArticle-1)+")","of",nArticles

                ## Title to be search in google scholar
                sItem['title'] = row.get('Title','') # 'The interaction of maturational constraints and intrinsic motivations in active motor development'
                sItem['nArticle'] = cArticle-1

                if not sItem['title']:
                    sItem['title'] = row.get('Article Title','')
                if not sItem['title']:
                    print 'Error with CSV identifier. It must contain either Title or Article Title'
                    exit()

                if options.resumee:
                    sItem['author'] = row.get('Authors','')
                    sItem['year'] = row.get('Year','')

                if options.lastTry is not None:
                    sItem['last-try'] = row.get(options.lastTry,'')
                    if not sItem['last-try']:
                        sItem['last-try'] = options.lastTry
                searchAndAppend(sItem,scQuerier,dict_writer,dict_writer_r)

                output_file.flush()
                if options.resumee:
                    resumee.flush()

                if not working:
                    print "\n\nError, probably communicating with google-scholar (your IP has been blocked).\nExiting...\n"
                    exit(1)

                cArticle += 1
        if options.resumee:
            resumee.close()
    else:
        sItem['title'] = title
        sItem['last-try'] = options.lastTry
        searchAndAppend(0,sItem,scQuerier,dict_writer)
