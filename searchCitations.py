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
import urllib

try:
    sys.path.insert(1, getcwd()+'../csv-articles/src/')
    import reformat
except ImportError:
    reformat = None 

# Retrieving command-line arguments
from searchCitations_Options import options

if options.notify:
    from ntfy import notify

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

def continueOrExit():
    if options.notify:
        notify('Check the search process!', 'SearchCitations.py says:')
    ask = raw_input('Do You Want To Accept (a), Pass (p) or run away? ')
    if ask == 'p':
        print "... passed!\n"
        return 1
    elif ask == 'a':
        print "... accepted.\n"
        return 0
    sys.exit(1)


def urlEncode(url):
    return urllib.quote_plus(url.encode('utf8'))

    http = 'http://'
    https = 'https://'
    if http in url:
        return http+urllib.quote_plus(url.replace(http,'').encode('utf8'))
    if https in url:
        return https+urllib.quote_plus(url.replace(https,'').encode('utf8'))
    return url

## Dictionary item
dItem = OrderedDict([('No. Citation',''),('Title',''),('First Author',''),('Authors',''),('Container',''),('Publisher',''),('Document Type',''),('DOI',''),('Volume',''),('Issue',''),('No. Article',''),('Crossref manual acceptance','')])
rItem = OrderedDict([('No. Article',''),('Title',''),('Author',''),('Search',''),('Forced year',''),('Cited by',''),('Found',''),('Scholar manual acceptance','')])
sItem = dict([('title',''),('author',''),('year',''),('year-forced',True),('last-try',''),('DOI',''),('manuallyAcceptedSc',''),('manuallyAcceptedCr',''),('nArticle',0),('scholarTest',0)])

def addItem(wtr,nCitation,title,authors='',container='',pub='',type='',doi='',vol='',issue='',nCitedArticle=0,manuallyAcceptedCr=''):
    if reformat:
        reformat.reformatAuthors(authors)

    dItem['No. Citation']       = nCitation
    dItem['Title']              = title
    dItem['First Author']       = authors.split(',')[0]
    dItem['Authors']            = authors
    dItem['Container']          = container
    dItem['Publisher']          = pub
    dItem['Document Type']      = type
    dItem['DOI']                = doi
    dItem['Volume']             = vol
    dItem['Issue']              = issue
    dItem['No. Article']        = nCitedArticle
    dItem['Crossref manual acceptance']   = manuallyAcceptedCr

    wtr.writerow(dItem)

def addItemResumee(wtr,resumeeItem):
    rItem = resumeeItem

    wtr.writerow(rItem)

def addItemResumee(wtr,nCitedArticle,title,author,citations,found=1,manuallyAcceptedSc='',search='',forcedYear=''):
    rItem['No. Article']   = nCitedArticle
    rItem['Title']         = title
    rItem['Author']        = author
    rItem['Search']        = search
    rItem['Forced year']   = forcedYear
    rItem['Cited by']      = citations
    rItem['Found']         = found
    rItem['Scholar manual acceptance']   = manuallyAcceptedSc

    wtr.writerow(rItem)

def searchAndAppend(search,querier,writer,writer_r='',tryAgain=True, previousWorked = False):
    global lastFromCrossref, working

    if search['scholarTest']:
        sEntry = 'robotics'
    else:
        sEntry = search['DOI'] if search['DOI'] else search['title']+' '+search['author']

    print 'Searching for',search['title']
    print '\t\t as',sEntry
    sYearEntry = ''

    ## Searching into scholar
    if search['year'] and search['year-forced']:
        print '\t\t ** forcing year as',search['year'],'**'
        scholarSearch = querier.search_pubs_query(sEntry,years=int(search['year']))
        sYearEntry = '&as_ylo='+search['year']+'&as_yhi='+search['year']
    else:
        scholarSearch = querier.search_pubs_query(sEntry)
    scholarFound = False
    scholarWorked = False
    count = 0   

    for i in range(MAX_SCHO):
        paper = next(scholarSearch,None)
        scholarWorked |= (i == 0 and (paper is not None))
        if paper is None or search['scholarTest']:
            break
        print "Scholar ("+str(i+1)+'/'+str(MAX_SCHO)+'):',paper.bib['title']

        if search['last-try']:
            search['title'] = search['title'].replace(' '+search['last-try'],'')
        count = 0

        titleComparison = compareTitles(cleanTitle(search['title'])[0:MAX_CHAR], cleanTitle(paper.bib['title'])[0:MAX_CHAR])
        scholarURL = 'https://scholar.google.com/scholar?q='+urlEncode(sEntry)+sYearEntry

        def unmatchRequest(text,scholarEntry, search = scholarURL, entry=sEntry):
            print 'Search: '+entry
            print text

            print '\n - author: '+scholarEntry.bib.get('author','')
            print ' - publisher: '+scholarEntry.bib.get('publisher','')
            print ' - volume: '+scholarEntry.bib.get('volume','')
            print ' - search URL: '+search
            print ' - entry URL: '+scholarEntry.bib.get('url','')
            print ' - entry ePrint: '+scholarEntry.bib.get('eprint','').replace('https://scholar.google.com','')
            print
            return continueOrExit()

        if not titleComparison:
            if unmatchRequest('** Unmatching title ** - Match below '+str(int(100*options.matcher))+'%',paper):
                print "Match: ",SequenceMatcher(None, cleanTitle(search['title'])[0:MAX_CHAR], cleanTitle(paper.bib['title'])[0:MAX_CHAR]).ratio()
                search['manuallyAcceptedSc'] += '-titlepass'
                continue
            search['manuallyAcceptedSc'] += '-title'

        # if compareTitles(cleanTitle(search['title'])[0:MAX_CHAR], cleanTitle(paper.bib['title'])[0:MAX_CHAR]):
        unmatch = True
        if search['author']:
            for author in paper.bib['author'].lower().split(', '):
                lastName = author.split(' ')
                if len(lastName)>1:
                    lastName = lastName[1]
                    initial = author[0]
                else:
                    initial = ''
                splittedAuthors = search['author'].lower().split(' ')
                lastName2 = splittedAuthors[0]
                initial2 = splittedAuthors[1][0] if splittedAuthors[1] else ''

                if not compareTitles(lastName,lastName2) or (initial and not initial == initial2):
                    print '\tUnmatching author:',paper.bib['author']
                    print '\tFrom found: ',
                    print initial,
                    print lastName,
                    print 'From search: ',
                    print initial2,
                    print lastName2
                    continue
                else:
                    unmatch = False
                    break

        if unmatch:
            if unmatchRequest('** Unmatching authors **',paper):
                search['manuallyAcceptedSc'] += '-authorspass'
                continue
            search['manuallyAcceptedSc'] += '-authors'

        if search['year'] and not search['year-forced'] and paper.bib['year'] != search['year']:
            if unmatchRequest('** Unmatching year **',paper):
                search['manuallyAcceptedSc'] += '-year'
                continue
            search['manuallyAcceptedSc'] += '-year'

        scholarFound = True
        print 'Found: ',paper.bib['title']
        print 'Authors:',paper.bib['author'],'('+initial2+' '+lastName2+')' if search['author'] else ''
        print 'Cited by:',paper.citedby
        
        if writer_r and lastFromCrossref == 0:
            addItemResumee(writer_r,search['nArticle'],search['title'],search['author'],paper.citedby,
                manuallyAcceptedSc=search['manuallyAcceptedSc'],search=sEntry,forcedYear=search['year'] if search['year-forced'] else '')

        if paper.citedby:
            ## Searching citations to article
            print
            print 'Searching cited by (starting from '+str(lastFromCrossref)+')'
            cb = paper.get_citedby(startAt=lastFromCrossref)
            count = lastFromCrossref

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

                cr_query = bibItem['title']+' '+bibItem['author'].replace('...','')
                cit_cleanTitle = cleanTitle(bibItem['title'].encode("ascii","ignore"))[0:MAX_CHAR]
                crSearch = cr.works(query=cr_query,limit=10)
                found = False

                search['manuallyAcceptedCr'] = ''

                for z in crSearch['message']['items']:
                    crTitle = z.get('title','')
                    if crTitle:
                        crTitle = crTitle[0]
                        if not crTitle.strip():
                            continue
                        authorData = reprintCrossReffAuthors(z.get('author',''))
                        print '\tCrossref item:\t',crTitle
                        print '\t\t\t\tBy: '+authorData
                        if compareTitles(cit_cleanTitle, cleanTitle(crTitle.encode("ascii","ignore"))[0:MAX_CHAR]):
                            if z.get('author',''):
                                match = False
                                for crAuthors in z.get('author',''):
                                    crAuthor = crAuthors.get('family','').lower().split(' ')
                                    if not crAuthor:
                                        break
                                    if isinstance(crAuthor,list):
                                        crAuthor = crAuthor[-1]
                                    if not crAuthor.strip():
                                        break
                                    for author in bibItem['author'].lower().split(', '):
                                        lastName = author.split(' ')
                                        if isinstance(lastName,list):
                                            lastName = lastName[-1]

                                        if compareTitles(cleanTitle(crAuthor.encode("ascii","ignore")), cleanTitle(lastName)):
                                            match = True
                                            break
                                        print 'Unmatching author:',lastName,'('+crAuthor.encode("ascii","ignore")+')'
                                    if match:
                                        break
                                if not match:
                                    if not crAuthor or not crAuthor.strip():
                                        continue
                                    print
                                    print 'Crossref search: '+'https://search.crossref.org/?q='+urlEncode(cr_query)
                                    print 'Crossref article URL: '+z.get('URL','')
                                    print 'Scholar URL: '+bibItem.get('url','')
                                    print 'Scholar ePrint: '+bibItem.get('eprint','').replace('https://scholar.google.com','')
                                    if continueOrExit():
                                        search['manuallyAcceptedCr'] += '-authorspass'
                                        continue
                                    search['manuallyAcceptedCr'] += '-authors'

                            print '\tDOI:\t\t',z['DOI']
                            print '\tSubject:\t',z.get('subject')

                            found = True
                            if not authorData:
                                authorData = bibItem['author']

                            cTitle = z.get('container-title','')
                            if cTitle:
                                cTitle = cTitle[0]

                            addItem(writer,count,z.get('title')[0],authors=authorData,container=cTitle,
                                pub=z.get('publisher',''),type=z.get('type',''),doi=z.get('DOI',''),
                                vol=z.get('volume',''),issue=z.get('issue',''),nCitedArticle=search['nArticle'],
                                manuallyAcceptedCr=search['manuallyAcceptedCr'])
                            break

                if not found:
                    print '\t*** Unable to find title in Crossref! ***'

                    addItem(writer,count,bibItem['title'],authors=bibItem['author'],pub=bibItem['publisher'],type='other',nCitedArticle=search['nArticle'])

                print
                count += 1
                lastFromCrossref = 0

            if count != paper.citedby:
                print "\n\nError communicating with google-scholar.\nExiting...\n"
                exit(404)
        break

    # print "Searching results: \n\tscholarFound:",scholarFound,"\n\tscholarWorked:",scholarWorked,"\n\tworking:",working,"\n\tpreviousWorked:",previousWorked
    # if paper:
    #     print "\tcount:",count,"\n\tcited by:",paper.citedby

    if not scholarFound:
        print '\nNot found!! ... ',

        if tryAgain and search['last-try']: # Still trying, there are words on 'last-try'
            print "Trying again with 'last-try' words ("+search['last-try']+")"
            search['title'] = search['title']+' '+search['last-try']
            searchAndAppend(search,querier,writer,writer_r, tryAgain=False, previousWorked=scholarWorked)

        else:
            if search['scholarTest']:
                print "Storing article in RESUMEE as not found (scholar searching is OK)"
                addItemResumee(writer_r,search['nArticle'],search['title'],search['author'],0,0)
                search['scholarTest'] = 0
                return
            if search['scholarTest'] and not scholarWorked:
                working = False # flag for exiting after searchAndAppend
                return


            if search['last-try']:
                print "Removing 'last try' from title"
                search['title'] = search['title'].replace(' '+search['last-try'],'')

            if search['year-forced']:
                print "Trying again but RELAXING YEAR"
                search['year-forced'] = False
                searchAndAppend(search,querier,writer,writer_r, tryAgain=True, previousWorked=scholarWorked)
                return

            # try again only to check if queries are working
            if previousWorked and not scholarWorked: 
                print "Trying again to see if scholar queries are working... "
                search['last-try'] = ''
                search['scholarTest'] = 1
                searchAndAppend(search,querier,writer,writer_r, tryAgain=False, previousWorked=scholarWorked)
                return

            if scholarWorked:
                print "Storing article in RESUMEE as not found (scholar searching is OK)"
                addItemResumee(writer_r,search['nArticle'],search['title'],search['author'],0,0)
            else:
                print "Trying again to see if scholar queries are working... "
                search['scholarTest'] = 1
                searchAndAppend(search,querier,writer,writer_r, tryAgain=False, previousWorked=scholarWorked)
                

def start_from_previous_work(saveNotFound=options.saveNotFound):
    # Check, clean and retreive information about existing data
    if path.exists(options.resumee) and path.exists(options.outFile):
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

            new_output = open(options.outFile+'2','wb')
            otherOutput = csv.DictWriter(new_output, dItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
            otherOutput.writeheader()

            if saveNotFound:
                nFound = open('notfound.csv','a')
                nfWriter = csv.DictWriter(nFound, rItem.keys(),encoding='utf-8',delimiter=options.outDelimiter)
                nfWriter.writeheader()

            print "previous: ",nArticles
            for row in reader:
                expected = int(row.get('Cited by','0'))
                rArticle = int(row.get('No. Article'))
                stored = 0
                for cB in range(expected):
                    try:
                        storedCitation = next(output_reader)
                        rArticle = int(storedCitation['No. Article'])
                        if int(storedCitation['No. Article']) == cArticle:
                            stored += 1
                            otherOutput.writerow(storedCitation)
                        else:
                            break
                    except Exception as e:
                        print e
                        break
                print "Stored/expected",stored,expected,"\t\tArticle number (from resumee and data)",rArticle,"-",cArticle
                if saveNotFound and row.get('Found','')=='0':
                    nfWriter.writerow(row)
                if expected == -1:
                    break
                if stored > 0 or (stored == 0 and expected == 0):
                    other.writerow(row)
                if stored != expected:
                    lastCitations = stored
                    break
                cArticle += 1


        rename(options.resumee+'2',options.resumee)
        rename(options.outFile+'2',options.outFile)

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
                    exit(1)

                print "\nArticle",cArticle,"("+str(cArticle-1)+")","of",nArticles

                ## Title to be search in google scholar
                sItem['title'] = row.get('Title','') # 'The interaction of maturational constraints and intrinsic motivations in active motor development'
                sItem['nArticle'] = cArticle-1
                sItem['DOI'] = row.get('DOI','')
                sItem['manuallyAcceptedSc'] = ''


                if not sItem['title']:
                    sItem['title'] = row.get('Article Title','')
                if not sItem['title']:
                    print 'Error with CSV identifier. It must contain either Title or Article Title'
                    exit(1)

                if options.resumee:
                    sItem['author'] = row.get('Authors','')
                    sItem['year'] = row.get('Year','')
                    sItem['year-forced'] = True

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
                    exit(404)

                cArticle += 1
        if options.resumee:
            resumee.close()
    else:
        sItem['title'] = options.title
        sItem['last-try'] = options.lastTry
        searchAndAppend(sItem,scQuerier,dict_writer)