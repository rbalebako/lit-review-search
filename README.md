# Literature Review Search Tool

A unified workflow for conducting systematic literature reviews using CrossRef, Scopus, and DBLP APIs to build citation networks from seed publications.

## Overview

This tool automatically:
1. Reads seed publication identifiers from a CSV file
2. Fetches publication metadata, references, and citations from multiple sources (CrossRef, Scopus, DBLP)
3. Builds a network of related publications
4. Filters publications by year range
5. Exports results to CSV files for further analysis

## Prerequisites

### API Keys

Create a `.env` file in the project root with the following configuration:

```env
# OpenCitations API Key (required for CrossRef citations/references)
OPENCITATIONS_API_KEY=your_opencitations_key_here

# CrossRef Configuration
CROSSREF_MAILTO=your_email@example.com

# Scopus API Key (optional, for Scopus fallback)
SCOPUS_API_KEY=your_scopus_key_here

# Review Configuration
REVIEW_NAME=firsttry
MIN_YEAR=2022
MAX_YEAR=2025
```

See `.env.example` for a template.

### Python Dependencies

```bash
pip install python-dotenv requests crossref-commons lxml
```

## Main Entry Point: run.py

`run.py` is the primary script for conducting literature reviews.

### Configuration

All configuration is loaded from environment variables in `.env`:

- **REVIEW_NAME**: Name of your review project (creates `data/{REVIEW_NAME}/` folder structure)
- **MIN_YEAR**: Minimum publication year (inclusive) for filtering related publications
- **MAX_YEAR**: Maximum publication year (inclusive) for filtering related publications

### Input File Format

Create a CSV file at `data/{REVIEW_NAME}/seeds.csv` with the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| Title  | At least one | Publication title |
| DOI    | At least one | Digital Object Identifier |
| EID    | At least one | Scopus EID |

Example:
```csv
Title,DOI,EID
"Machine Learning in Healthcare","10.1234/example",""
"Deep Learning for Diagnosis","","2-s2.0-85012345678"
"AI Medical Applications","10.5678/sample",""
```

### Workflow

#### 1. Process Seed Publications

For each seed publication:
1. **Search Strategy** (tries in order):
   - Search by title in DBLP and Scopus
   - Search by DOI in CrossRef
   - Search by EID in Scopus
2. **Validation**: Ensures publication has references OR citations
3. **Metadata Extraction**: Retrieves title, year, abstract, authors, venue
4. **Citation Network**: Collects all references and citations

#### 2. Collect Related Publications

- Aggregates all unique DOIs/EIDs from seed publications' references and citations
- Saves to `data/{REVIEW_NAME}/seed_related_ids.txt`

#### 3. Process Related Publications

For each related publication:
1. **Identify Source**: Determines if ID is DOI or EID
2. **Fetch Metadata**: Retrieves publication details
3. **Year Filtering**: Only caches publications within `[MIN_YEAR, MAX_YEAR]` range
4. **Save**: Appends to publications CSV

### Output Files

#### `data/{REVIEW_NAME}/publications.csv`

Contains metadata for all processed publications:

| Column | Description |
|--------|-------------|
| title | Publication title |
| doi | Digital Object Identifier |
| eid | Scopus EID |
| dblp | DBLP key |
| year | Publication year |
| citation_count | Number of citations |
| reference_count | Number of references |
| url | DOI URL |
| abstract | Publication abstract (from arXiv if available) |

#### `data/{REVIEW_NAME}/seed_related_ids.txt`

Plain text file with one DOI/EID per line - all publications cited by or citing seed publications.

### Usage

```bash
# 1. Configure .env file
cp .env.example .env
# Edit .env with your API keys and settings

# 2. Prepare seed publications CSV
mkdir -p data/myreview
# Create data/myreview/seeds.csv with your seed publications

# 3. Run the tool
python run.py
```

### Example Output

```
Getting list of seed studies from data/firsttry/seeds.csv...
Found 3 seed publications
** Searching by title: Machine Learning in Healthcare
** Searching DBLP for: Machine Learning in Healthcare
Found in DBLP: conf/icml/SmithJ23
** Found valid publication by title: Machine Learning in Healthcare
  Processing DOI: 10.1145/3576915.3623157, title: Machine Learning in Healthcare
    Title: Machine Learning in Healthcare
    Year: 2023
    References: 45
    Citation count: 12
  10.1145/3576915.3623157: 57 related publications

Total unique related publications: 142
Results saved to: data/firsttry/seed_related_ids.txt
  Skipping doi:10.1234/old-paper: year 2015 outside range [2022, 2025]
  Processing DOI: 10.5678/recent-paper, title: Recent Advances
  ...
```

## Key Features

### Multi-Source Search Strategy

The tool intelligently searches across multiple academic databases:

1. **DBLP**: Computer science publications, excellent for conference papers
2. **CrossRef**: General academic publications, comprehensive DOI coverage
3. **Scopus**: Broad academic coverage, strong citation data

### Automatic Fallback

If one data source fails or has incomplete data, the tool automatically tries alternative sources using available identifiers (DOI, EID, title).

### Citation Network Building

- Uses OpenCitations API for CrossRef citation/reference data
- Aggregates forward citations (papers citing this work)
- Aggregates backward citations (papers this work references)

### Year-Based Filtering

Related publications are filtered by year to focus on recent literature:
- Publications outside `[MIN_YEAR, MAX_YEAR]` are logged but not cached
- Publications with unknown years are cached with a warning

### Abstract Enrichment

Automatically attempts to fetch abstracts from arXiv when not available from primary sources.

## Advanced Features

### Rate Limiting

Built-in 3-second delay between API requests (configurable in code):

```python
time.sleep(3)  # Adjust as needed
```

### Citation Validation

Publications must have either references OR citations to be considered valid:

```python
def has_citations(pub, service_name):
    ref_count = pub.reference_count
    cite_count = pub.citation_count
    return cite_count > 0 or ref_count > 0
```

### Publication Factory Pattern

`create_publication()` tries multiple search strategies and data sources automatically:

```python
pub = create_publication(doi="10.1234/example", eid=None, title="Paper Title")
```

## Project Structure

```
lit-review-search/
├── run.py                          # Main workflow script
├── publication.py                  # Base publication class
├── crossref_publication.py         # CrossRef implementation
├── scopus_publication.py           # Scopus implementation
├── dblp_publication.py            # DBLP implementation
├── .env                           # Configuration (not in git)
├── .env.example                   # Configuration template
├── data/
│   └── {REVIEW_NAME}/
│       ├── seeds.csv              # Input: seed publications
│       ├── publications.csv       # Output: all publication metadata
│       └── seed_related_ids.txt   # Output: related publication IDs
└── README.md
```

## Troubleshooting

### "OPENCITATIONS_API_KEY not found"
- Create `.env` file with your OpenCitations API key
- Get a free key from https://opencitations.net/

### "No valid publication data found"
- Verify the DOI/EID/title in the input CSV
- Check that the publication exists in the queried databases
- Ensure the publication has citation data (some very new papers may not)

### "Error creating CrossRef/Scopus/DBLP publication"
- Check API keys in `.env`
- Verify network connectivity
- Check API rate limits (add longer delays if needed)

### Publications not filtered by year
- Verify `MIN_YEAR` and `MAX_YEAR` are set in `.env`
- Check that publications have valid year metadata
- Publications with unknown years are included by default

## History and Motivation

I originally forked this from janinaj/lit-review-search, with a strong desire to use the method described for a literature review.  However, I soon found that my biggest problem was finding the publications I wanted in Scopus.  (Of the 4 seed pubs, SCOPUS had only 1).  I then added crossref and DBLP search APIs.  These were more likely to find the publications, but did not contain references and citations.  
It may have been easier to start by scraping Google or Arxiv after all. In this final implementation, I only scrape Arxiv to get the abstract, and even then I only get about 10% of abstracts.  

## License
GNU GENERAL PUBLIC LICENSE
