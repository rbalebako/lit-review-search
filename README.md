# Literature Review Search Tool

This tool provides a unified workflow for conducting systematic literature reviews using both CrossRef and Scopus APIs to build citation networks from seed publications.

## Overview

The tool automatically:
1. Reads seed publication identifiers from a CSV file
2. Fetches publication metadata, references, and citations from CrossRef (with Scopus fallback)
3. Builds a network of related publications
4. Exports results to CSV and text files for further analysis

## Main Entry Point: run.py

`run.py` is the primary script for conducting literature reviews. It orchestrates the entire workflow:

### Workflow Steps

1. **Load Seed Publications**: Reads DOIs/identifiers from `data/{reviewname}/seed-studies/{reviewname}/included.csv`
2. **Fetch Metadata**: For each seed publication:
   - Attempts to retrieve data from CrossRef API
   - Falls back to Scopus API if CrossRef data is unavailable or incomplete
   - Validates that both references and citations are present
3. **Cache Publication Data**: Saves publication metadata (title, year, abstract, citation count) to `output/publications.csv`
4. **Build Citation Network**: Collects all unique DOIs from references and citations
5. **Export Results**: Saves list of related publication IDs to `data/{reviewname}/related-ids/seed_related_ids.txt`

### Usage

```bash
python run.py
```

### Configuration

Edit the `main()` function in `run.py` to configure:

```python
reviewname = 'firsttry'              # Name of your review project
min_year = 2022                       # Minimum publication year
max_year = 2025                       # Maximum publication year
shared = 0.10                         # Threshold for co-citation analysis (10%)
```

### Input File Format

The seed publications CSV should have columns including either `DOI` or `ID`:

```csv
Title,EID,DOI
"Paper Title","Scopus EID","DOI"
```

### Output Files

1. **`output/publications.csv`**: Metadata for all processed seed publications
   - Columns: id, title, year, abstract, citation_count

2. **`data/{reviewname}/related-ids/seed_related_ids.txt`**: List of all unique publication IDs related to seeds
   - One DOI per line
   - Includes all references and citations from seed publications

## Key Features

- **Dual API Support**: Automatically tries CrossRef first, falls back to Scopus
- **Validation**: Ensures publications have both references and citations before including them
- **Citation Network Analysis**: Functions for co-citation and bibliographic coupling analysis
- **Rate Limiting**: Built-in delays to respect API rate limits
- **Caching**: Stores downloaded data locally to avoid redundant API calls

## Module Structure

- **`publication.py`**: Base class for publications with common functionality
- **`crossref_publication.py`**: CrossRef API implementation with OpenCitations integration
- **`scopus_publication.py`**: Scopus API implementation
- **`run.py`**: Main orchestration script

## Key Functions in run.py

- `read_seed_csv(input_file)`: Parse seed publication identifiers from CSV
- `create_publication(data_folder, identifier)`: Factory function to create publication objects
- `validated_publication(pub, identifier, service_name)`: Verify publication has valid citation data
- `cache_pub_metadata(seed_id, output_folder)`: Fetch and save publication metadata
- `save_related_ids_csv(all_related_ids, output_folder)`: Export related publication IDs
- `get_strong_citation_relationship(pub, shared)`: Identify strongly-related publications

## Requirements

### Environment Variables

Create a `.env` file with:

```env
OPENCITATIONS_API_KEY=your_opencitations_key
CROSSREF_MAILTO=your_email@example.com
SCOPUS_API_KEY=your_scopus_key  # Optional, for Scopus fallback
```

### Python Dependencies

```bash
pip install python-dotenv
pip install requests
pip install crossref-commons
pip install lxml  # For Scopus XML parsing
```

## Advanced Usage

### Co-Citation Analysis

The tool includes functions for identifying publications with strong co-citation relationships:

```python
# Get publications that strongly co-cite the target paper
strong_co_citing = get_strong_co_citing(pub, shared=0.10)

# Get publications strongly co-cited with the target paper
strong_co_cited = get_strong_co_cited(pub, shared=0.10)

# Get all strongly-related publications
strong_related = get_strong_citation_relationship(pub, shared=0.10)
```


## Troubleshooting

- **"No valid publication data found"**: The DOI may not exist in CrossRef/Scopus, or the publication lacks references/citations
- **API Rate Limit Errors**: Increase the `time.sleep()` value in the main loop
- **Missing Abstract**: The tool attempts to scrape abstracts from publisher pages when not available in CrossRef metadata

## Project Structure

```
lit-review-search/
├── run.py                      # Main entry point
├── publication.py              # Base publication class
├── crossref_publication.py     # CrossRef implementation
├── scopus_publication.py       # Scopus implementation
├── data/
│   └── {reviewname}/
│       ├── seed-studies/       # Input seed publication lists
│       └── related-ids/        # Output related publication IDs
└── output/
    └── publications.csv        # Cached publication metadata
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
