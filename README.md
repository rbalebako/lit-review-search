# Literature Review Search System

A Python-based automated literature review tool that uses citation network analysis and keyword filtering to identify relevant publications from seed papers. Supports both **Scopus API** and **CrossRef API**.

## Overview

This system implements a multi-stage filtering approach to expand a small set of seed publications into a larger corpus of related papers for literature reviews. It combines:

1. **Citation Network Analysis** - Direct references, citations, and co-citation relationships
2. **Keyword Extraction** - RAKE (Rapid Automatic Keyword Extraction) from abstracts
3. **Topic Modeling** - Optional HDP (Hierarchical Dirichlet Process) based filtering

## Data Sources

### Scopus API
- **Access:** Requires API key and institutional subscription
- **Coverage:** Comprehensive citation data including full citing works
- **Best for:** Complete citation network analysis
- **Sign up:** https://dev.elsevier.com/

### CrossRef API
- **Access:** Free and open, no API key required
- **Coverage:** Full reference lists, citation counts 
- **Best for:** Reference-based analysis, open science projects
- **Documentation:** https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- **Python library: CrossRef Commons for python  https://gitlab.com/crossref/crossref_commons_py

### OpenCitations API
- ** Best For:** Citations and References
- ** Documentation:** https://opencitations.net

## Requirements

1. **Python 3.9+** (updated from Python 2)
2. **API Access:**
   - **Scopus API Key** (optional) - For complete citation networks
   - **CrossRef mailto** (optional) - For faster API access (polite pool)
   - **OpenCitations API Key** 
3. **Python Dependencies:**
   - lxml
   - python-dotenv
   - rake-nltk
   - (Optional) HDP binary and R for topic modeling

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd lit-review-search

# Install dependencies
pip3 install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your Scopus API key
```

### Environment Configuration

Create a `.env` file in the project root with your Scopus API key:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your credentials:

```ini
# Scopus API Configuration
SCOPUS_API_KEY=your_actual_api_key_here

# Optional: Current year for citation filtering (defaults to current year)
CURRENT_YEAR=2018
```

**Security Note:** The `.env` file is automatically ignored by git and will never be committed to your repository.

## How It Works

### System Architecture

```
Input Seed Papers → Citation Network Download → Network Expansion → Filtering → Results
```

### Core Components

#### 1. ScopusPublication Class (`scopus_publication.py`)

The central data model that handles all publication data and Scopus API interactions.

**Key Features:**
- Downloads and caches publication metadata, references, and citations from Scopus API
- Extracts abstracts and publication years
- Computes co-citation and co-citing relationships
- Implements rate limiting (5-second delays between API calls)

**Data Stored Per Publication:**
```
data/scopus-download/{eid}/
├── references.xml              # Abstract and references from Scopus
├── rake_keywords.txt           # Extracted keywords
├── top_shared.txt              # Strong citation relationships
└── citations/
    ├── 1900-0.json
    ├── 2018-5.json
    └── ...
```

**Properties:**
- `eid` - Scopus publication ID
- `references` - Publications this paper cites
- `citations` - Papers that cite this publication
- `co_citing_counts` - Papers that cite the same references
- `co_cited_counts` - Papers cited by the same citations
- `abstract` - English abstract text
- `pub_year` - Publication year

#### 2. Citation Filtering (`citation_filtering.py`)

Computes "strong citation relationships" based on citation network structure.

**Algorithm:**
```python
For a seed paper S:

Strong Citation Space includes:
├── Direct References: Papers S cites
├── Direct Citations: Papers that cite S
├── Co-citing: Papers citing >= 10% of S's references
│   (Papers discussing similar prior work)
└── Co-cited: Papers cited by >= 10% of papers citing S
    (Papers related to topics S discusses)
```

**Key Functions:**
- `get_strong_co_citing(scopus_pub, shared)` - Find papers that cite many of the same references
- `get_strong_co_cited(scopus_pub, shared)` - Find papers cited by many of the same papers
- `get_strong_citation_relationship(scopus_pub, shared)` - Combine all strong relationships

**Threshold Parameter:**
- `shared = 0.10` means papers must share at least 10% of references/citations to be considered "strongly related"

#### 3. Keyword Extraction (`keywords.py`)

Extracts keywords from abstracts using RAKE algorithm.

**Workflow:**
1. Load publication abstract
2. Apply RAKE to extract ranked keyword phrases
3. Save keywords to `rake_keywords.txt`
4. One keyword per line, ranked by importance

#### 4. Topic Modeling (`topic_filtering.py`)

Optional topic-based filtering using HDP (Hierarchical Dirichlet Process).

**Note:** Requires external HDP binary and R script (not fully implemented).

### Orchestration Scripts

#### `run.py` - Main Citation-Based Pipeline

Basic workflow using only citation network expansion.

**Configuration:**
```python
shared = 0.10               # Co-citation threshold (10%)
year = 2013                 # Filter citations before this year
review = '84925226708'      # Review identifier (folder name)
studies_folder = 'data/included-studies'
output_folder = 'data/scopus-download'
```

**Workflow:**
1. Load seed papers from `data/included-studies/{review}/included.csv`
2. For each seed, create ScopusPublication object (downloads metadata)
3. Filter citations by year
4. Compute strong citation relationships for each seed

**Input Format (`included.csv`):**
```
Title,EID
"Paper Title 1",85012345678
"Paper Title 2",85023456789
```

#### `run_keyword.py` - Citation + Keyword Filtering

Extends `run.py` with keyword-based filtering.

**Additional Steps:**
5. Union all strong citation spaces from all seeds
6. Load ScopusPublication for each related paper
7. Extract RAKE keywords from seed papers (2-3 word phrases only)
8. Filter related papers by keyword overlap with seeds
9. Write results to `rake_results.csv`

**Output Format (`rake_results.csv`):**
```
SCOPUS_ID    TITLE                      ABSTRACT
85012345678  "Related Paper Title"      "Abstract text..."
85023456789  "Another Paper"            "More abstract..."
```

#### `run_topic_model.py` - Citation + Topic Modeling

Extends `run.py` with HDP topic modeling (incomplete implementation).

**Additional Steps:**
5. Run HDP topic modeling on related papers
6. Cluster documents by topic
7. Select relevant topic clusters

**Status:** Requires external HDP tools and is not fully functional.

### CrossRef Module

#### `crossref_publication.py` - CrossRef Data Model

Similar to ScopusPublication but uses DOI identifiers and the free CrossRef API.

**Key Features:**
- No API key required (free and open access)
- Downloads publication metadata, references, and abstracts
- Uses DOI as primary identifier
- Supports "polite pool" for faster API access (with email)
- Built-in search by title or author

**Properties:**
- `doi` - Digital Object Identifier
- `references` - Publications this paper cites (full list available)
- `citation_count` - Number of citations (count only, not full list)
- `abstract` - Abstract text
- `pub_year` - Publication year
- `title` - Publication title

**Limitations:**
- Full list of citing works requires CrossRef Cited-by membership
- Citation counts available, but not citing paper details
- Consider integrating with OpenCitations for free citation data

**Search Functions:**
```python
# Search by title
results = CrossRefPublication.search_by_title("machine learning", data_folder)

# Search by author
results = CrossRefPublication.search_by_author("Jane Smith", data_folder, max_results=20)

# Get publication by DOI
pub = CrossRefPublication(data_folder, "10.1037/0003-066X.59.1.29")
```

#### `run_crossref.py` - CrossRef Pipeline

Basic workflow using CrossRef API for citation network expansion.

**Configuration:**
```python
shared = 0.10                # Co-citation threshold (10%)
min_year = 2010              # Minimum year
max_year = 2020              # Maximum year
review = 'crossref-review'   # Review identifier (folder name)
studies_folder = 'data/included-studies'
output_folder = 'data/crossref-download'
```

**Input Format (`included.csv`):**
```csv
Title,DOI
"Paper Title 1","10.1037/0003-066X.59.1.29"
"Paper Title 2","10.1234/example.doi"
```

**Workflow:**
1. Load seed papers from `data/included-studies/{review}/included.csv`
2. For each seed, create CrossRefPublication object (downloads metadata)
3. Extract references (works cited)
4. Filter by year range
5. Compute strong citation relationships based on references

**Output:**
- Cached metadata in `data/crossref-download/{doi}/`
- List of related DOIs in `data/crossref_related_dois.txt`

## Usage

### Unified CSV Format

Both Scopus and CrossRef modules use the **same CSV input format** for maximum flexibility:

```csv
Title,EID,DOI
"Paper Title","Scopus EID","DOI"
```

- **Scopus scripts** (run.py, run_keyword.py, run_topic_model.py) read **column 2 (EID)**
- **CrossRef script** (run_crossref.py) reads **column 3 (DOI)**

This allows you to:
- ✅ Use the same input file for both APIs
- ✅ Switch between Scopus and CrossRef without reformatting
- ✅ Provide both identifiers for comprehensive coverage
- ✅ Leave columns empty if only using one API

---

### Using Scopus API

### Step 1: Prepare Input Data

Create a CSV file with seed publications. The file uses a **unified format** that works with both Scopus and CrossRef:

```bash
mkdir -p data/included-studies/my-review
```

Create `data/included-studies/my-review/included.csv`:
```csv
Title,EID,DOI
"First Seed Paper","85012345678","10.1037/0003-066X.59.1.29"
"Second Seed Paper","85023456789","10.1234/example.doi"
"Paper with only EID","85034567890",""
"Paper with only DOI","","10.5678/another.doi"
```

**CSV Format:**
- **Column 1 (Title):** Publication title
- **Column 2 (EID):** Scopus EID - used by Scopus scripts (run.py, run_keyword.py, etc.)
- **Column 3 (DOI):** Digital Object Identifier - used by CrossRef script (run_crossref.py)

**Tips:**
- You can provide both EID and DOI for maximum flexibility
- Leave EID empty (`""`) if using only CrossRef
- Leave DOI empty (`""`) if using only Scopus
- The script you run determines which column is used

**Finding Scopus EIDs:**
1. Search for paper on Scopus.com
2. The EID is in the URL: `scopus.com/record/display.uri?eid=2-s2.0-85012345678`
3. Use the numeric part only: `85012345678`

**Finding DOIs:**
1. Search for paper on CrossRef.org, Google Scholar, or journal website
2. DOI format: `10.xxxx/xxxxxx`
3. Example: `10.1037/0003-066X.59.1.29`

### Step 2: Configure Environment Variables

Make sure you've created your `.env` file with your Scopus API key (see Installation section above):

```bash
# Copy the example file if you haven't already
cp .env.example .env

# Edit the .env file with your actual API key
# SCOPUS_API_KEY=your_actual_api_key_here
```

### Step 3: Configure Run Script

Edit `run.py` (or `run_keyword.py`):
```python
review = 'my-review'  # Must match folder name in step 1
studies_folder = 'data/included-studies'
output_folder = 'data/scopus-download'
shared = 0.10    # Co-citation threshold (10%)

# Citation year range filter (inclusive)
min_year = 2010  # Minimum year, use None for no lower bound
max_year = 2020  # Maximum year, use None for no upper bound

# Examples:
# min_year = 2010, max_year = 2020  # Only citations from 2010-2020
# min_year = None, max_year = 2015  # All citations up to 2015
# min_year = 2010, max_year = None  # All citations from 2010 onwards
# min_year = None, max_year = None  # No year filtering
```

### Step 4: Run the Pipeline

```bash
# Basic citation network expansion
python3 run.py

# With keyword filtering (recommended)
python3 run_keyword.py

# With topic modeling (requires HDP tools)
python3 run_topic_model.py
```

### Step 5: Review Results

**Citation network data:**
- Stored in `data/scopus-download/{eid}/`
- Each publication has its own folder with XML and JSON files

**Filtered results (from run_keyword.py):**
- `rake_results.csv` - Tab-separated file with filtered publications
- Columns: SCOPUS_ID, TITLE, ABSTRACT

---

### Using CrossRef API

#### Step 1: Prepare Input Data

Use the **same unified CSV format** as Scopus. CrossRef scripts read the DOI column (third column):

```bash
mkdir -p data/included-studies/crossref-review
```

Create `data/included-studies/crossref-review/included.csv`:
```csv
Title,EID,DOI
"First Seed Paper","85012345678","10.1037/0003-066X.59.1.29"
"Second Seed Paper","85023456789","10.1234/example.doi"
"Paper with only DOI","","10.5678/another.doi"
```

**Note:** CrossRef uses the DOI column (column 3). The EID column can be empty or omitted for CrossRef-only workflows.

**Backward Compatibility:** If you have an old format with only 2 columns (Title,DOI), it will still work.

#### Step 2: Configure Environment Variables (Optional)

For faster API access, add your email to `.env`:

```bash
# Edit .env file
CROSSREF_MAILTO=your_email@example.com
```

This enables "polite pool" access with higher rate limits (50 req/sec vs 5 req/sec).

**Note:** No API key required - CrossRef API is free and open!

#### Step 3: Configure Run Script

Edit `run_crossref.py`:
```python
review = 'crossref-review'  # Must match folder name
studies_folder = 'data/included-studies'
output_folder = 'data/crossref-download'
shared = 0.10    # Co-citation threshold (10%)

# Citation year range filter (inclusive)
min_year = 2010
max_year = 2020
```

#### Step 4: Run the Pipeline

```bash
python3 run_crossref.py
```

#### Step 5: Review Results

**Cached metadata:**
- Stored in `data/crossref-download/{doi}/metadata.json`
- Each DOI has its own folder with JSON metadata

**Related publications:**
- `data/crossref_related_dois.txt` - List of related DOIs

**Note:** CrossRef API provides full reference lists but only citation counts (not full citing works) without membership. For complete citation networks, use Scopus API or integrate with OpenCitations.

## Data Flow Diagram

```
┌─────────────────────────────────────────┐
│ INPUT: included.csv                     │
│ Format: Title,EID                       │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│ PHASE 1: Download Citation Networks     │
│ • Query Scopus API for each seed        │
│ • Download references.xml               │
│ • Download citations (paginated JSON)   │
│ • Cache all data locally                │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│ PHASE 2: Citation Filtering             │
│ • Filter citations by year              │
│ • Calculate co-citing relationships     │
│ • Calculate co-cited relationships      │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│ PHASE 3: Strong Citation Relationships  │
│ • Direct references                     │
│ • Direct citations                      │
│ • Strongly co-citing papers (≥10%)      │
│ • Strongly co-cited papers (≥10%)       │
└─────────────┬───────────────────────────┘
              │
              ↓ (Optional: run_keyword.py)
┌─────────────────────────────────────────┐
│ PHASE 4: Keyword Extraction             │
│ • Extract RAKE keywords from abstracts  │
│ • Filter to 2-3 word phrases            │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│ PHASE 5: Keyword-Based Filtering        │
│ • Compare keywords of related papers    │
│ • Keep papers with keyword overlap      │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│ OUTPUT: rake_results.csv                │
│ Format: SCOPUS_ID<TAB>TITLE<TAB>ABSTRACT│
└─────────────────────────────────────────┘
```

## Configuration Parameters

### Citation Network Settings

```python
shared = 0.10  # Co-citation threshold
               # 0.10 = papers must share 10% of references/citations
               # Higher values = stricter filtering, fewer papers
               # Lower values = more papers, potentially less related

# Citation year range filter (both bounds are inclusive)
min_year = 2010  # Minimum publication year
                 # Set to None for no lower bound
                 # Example: 2010 includes papers from 2010 onwards

max_year = 2020  # Maximum publication year
                 # Set to None for no upper bound
                 # Example: 2020 includes papers up to and including 2020

# Common year range configurations:
# min_year = 2010, max_year = 2020  → Only 2010-2020 (inclusive)
# min_year = None, max_year = 2015  → All papers up to 2015
# min_year = 2010, max_year = None  → Papers from 2010 onwards
# min_year = None, max_year = None  → No temporal filtering
```

### File Paths

```python
review = '84925226708'  # Folder name for this literature review
                        # Can be any identifier, not necessarily a Scopus ID

studies_folder = 'data/included-studies'
                # Contains {review}/included.csv with seed papers

output_folder = 'data/scopus-download'
               # Cache folder for all downloaded Scopus data
```

## API Rate Limits and Caching

### Scopus API Calls

The system makes two types of Scopus API requests:

1. **Abstract/Reference Retrieval:**
   ```
   GET https://api.elsevier.com/content/abstract/scopus_id/{eid}
   Response: XML with abstract, metadata, and references
   ```

2. **Citation Search:**
   ```
   GET https://api.elsevier.com/content/search/scopus
   Query: refeid(2-s2.0-{eid})
   Response: JSON with citing papers
   ```

### Rate Limiting

- **Built-in delay:** 5 seconds between requests
- **Scopus limits:** Check your API subscription for specific limits
  - Typical institutional access: 5,000-10,000 requests/week

### Caching Strategy

All API responses are cached to disk:
- **First run:** Downloads all data from Scopus API (slow)
- **Subsequent runs:** Uses cached data (fast)
- **Cache location:** `data/scopus-download/{eid}/`

To re-download data for a specific publication, delete its folder.

## Scaling Considerations

### Citation Network Growth

Starting with N seed papers can result in exponential expansion:

```
Seed Papers: 5
↓
Direct Citations + References: ~50-100 papers each = 250-500 papers
↓
Co-citing + Co-cited (10% threshold): ~500-2,000 papers
↓
With Keyword Filtering: ~100-500 papers
```

### API Request Estimates

For N seed papers:
- **Reference downloads:** N requests
- **Citation downloads:** N × years × pages ≈ N × 20-100 requests
- **Co-citation analysis:** May recursively download more papers

**Example:** 5 seed papers could require 500-1,000 API requests.

### Runtime Estimates

- **Initial download:** 2-5 minutes per seed paper (depends on citations)
- **Cached analysis:** 10-30 seconds per seed paper
- **Total for 5 seeds:** 30-60 minutes first run, < 1 minute subsequent runs

## Troubleshooting

### API Key Issues

**Error:** `ValueError: SCOPUS_API_KEY not found in environment variables`

**Solutions:**
1. Make sure you've created a `.env` file in the project root
2. Copy `.env.example` to `.env`: `cp .env.example .env`
3. Edit `.env` and add your actual API key
4. Ensure the `.env` file is in the same directory as the Python scripts

**Error:** `Error getting reference file: {eid}` or `401 Unauthorized`

**Solutions:**
1. Verify your API key is correct in the `.env` file
2. Check API key has citation search permissions on the Elsevier Developer Portal
3. Verify institutional access to Scopus
4. Check if API key has expired or reached rate limits

### Missing Data

**Error:** `KeyError: 'entry'` or empty results

**Possible Causes:**
1. Publication has no citations
2. Publication not indexed in Scopus
3. API rate limit exceeded

**Solution:** Check the cached XML/JSON files in `data/scopus-download/{eid}/`

### Encoding Errors (Python 2 to 3 Migration)

**Error:** `TypeError: a bytes-like object is required, not 'str'`

**Solution:** The codebase has been updated for Python 3. Ensure you're using Python 3.9+:
```bash
python3 --version
python3 run.py  # Not python run.py
```

### Empty Keyword Results

**Issue:** `rake_keywords.txt` is empty

**Causes:**
1. Abstract is empty or not in English
2. RAKE failed to extract meaningful phrases

**Solution:** Check the abstract in `references.xml` - some papers may not have abstracts in Scopus.

## File Structure Reference

```
lit-review-search/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
│
├── scopus_publication.py          # Core data model and API interactions
├── citation_filtering.py          # Citation network analysis
├── keywords.py                    # RAKE keyword extraction
├── topic_filtering.py             # HDP topic modeling
│
├── run.py                         # Main pipeline (citation only)
├── run_keyword.py                 # Pipeline with keyword filtering
├── run_topic_model.py             # Pipeline with topic modeling
│
└── data/
    ├── included-studies/
    │   └── {review_id}/
    │       └── included.csv       # INPUT: Seed papers
    │
    └── scopus-download/
        └── {eid}/
            ├── references.xml     # Cached Scopus abstract + references
            ├── rake_keywords.txt  # Extracted keywords
            ├── top_shared.txt     # Strong citation relationships
            └── citations/
                ├── 1900-0.json    # Cached citation search results
                └── ...
```

## Citation

This implementation is based on the following paper:

**Testing a Citation and Text-Based Framework for Retrieving Publications for Literature Reviews**

Maria Janina Sarol, Linxi Liu, and Jodi Schneider

Proceedings of the 7th International Workshop on Bibliometric-enhanced Information Retrieval (2018)

Link to full paper: http://ceur-ws.org/Vol-2080/paper3.pdf

### BibTeX Citation

```bibtex
@inproceedings{SarolLS18,
  author    = {Maria Janina Sarol and
               Linxi Liu and
               Jodi Schneider},
  title     = {Testing a Citation and Text-Based Framework for Retrieving Publications for Literature Reviews},
  booktitle = {Proceedings of the 7th International Workshop on Bibliometric-enhanced
               Information Retrieval},
  pages     = {22--33},
  year      = {2018},
  url       = {http://ceur-ws.org/Vol-2080/paper3.pdf}
}
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check the Troubleshooting section above
- Review the paper: http://ceur-ws.org/Vol-2080/paper3.pdf
- [Add contact information or issue tracker link]
