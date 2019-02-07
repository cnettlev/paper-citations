# paper_citations
A python implementation that uses google-scholar citations to fulfill an output csv file with crossref data (or just scholar). 

The current version uses scholarly to query google scholar (from https://github.com/cnettlev/scholarly) and habanero as a Crossref python API.

# Usage
> ```
> searchCitations.py -i INPUT_CSV [OPTIONS]
> ```
> or
> ```
> searchCitations.py -t ARTICLE_TITLE [OPTIONS]
> ```

### Usage options
> ```
>   -h, --help            show this help message and exit
>   
>   -d DEL, --delimiter=DEL
>                         (Optional) Delimiter to be use with both, INPUT_CSV
>                         and OUTPUT_CSV. To use \t or other similar special
>                         characters in bash use $'\t'. [default: ,]
>                         
>   --delimiter-input=iDEL
>                         (Optional) Delimiter to be use with INPUT_CSV.
>                         Overwrites -d DELIMITER option.
>                         
>   --delimiter-output=oDEL
>                         (Optional) Delimiter to be use with OUTPUT_CSV.
>                         Overwrites -d DELIMITER option.
>                         
>   -i INPUT_CSV, --input=INPUT_CSV
>                         Name of the CSV file containing a list of articles to
>                         get citations for. This file must contain a data
>                         identifier named "Title" or "Article Title".
>                         
>   -m MATCH, --match-percent=MATCH
>                         When titles are compared, a matching percentage can be
>                         use, to avoid hard exact comparitons. [default: 1]
>                         
>   -l LAST_TRY, --lastTry=LAST_TRY
>                         (Optional) If INPUT_CSV is given, another identified
>                         named as LAST_TRY is appended to a title if the title
>                         alone is not enough for finding the article. If there
>                         is no identifier in the CSV file or ARTICLE_TITLE is
>                         given, LAST_TRY is appended to the title.
>                         
>   -o OUTPUT_CSV, --output=OUTPUT_CSV
>                         (Optional) Name of the output CSV file containing the
>                         articles citing the list from INPUT_CSV. By default,
>                         the file uses the INPUT_CSV name as "cit_INPUT_CSV"
>                         or, similarly, the ARTICLE_TITLE.
>                         
>   -t ARTICLE_TITLE, --title=ARTICLE_TITLE
>                         Instead of a CSV file, a single title can be used for
>                         searching citing articles.> 
> ```
