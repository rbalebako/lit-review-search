import sys, os, math
from crossref_publication import CrossRefPublication

def get_strong_co_citing(crossref_pub, shared):
    """
    Return DOIs of publications that are strongly co-citing with the given publication.

    Args:
        crossref_pub: CrossRefPublication object whose co-citing counts are examined.
        shared: float fraction used to compute the minimum shared reference threshold.

    Returns:
        List of DOI strings for publications with co-citing counts >= threshold.
    """
    min_count = math.ceil(crossref_pub.reference_count * shared)

    dois = []
    for doi, count in list(crossref_pub.co_citing_counts.items()):
        if count >= min_count:
            dois.append(doi)

    return dois

def get_strong_co_cited(crossref_pub, shared):
    """
    Return DOIs of publications that are strongly co-cited with the given publication.

    Args:
        crossref_pub: CrossRefPublication object whose co-cited counts are examined.
        shared: float fraction used to compute the minimum shared citation threshold.

    Returns:
        List of DOI strings for publications with co-cited counts >= threshold.
    """
    min_count = math.ceil(crossref_pub.citation_count * shared)

    dois = []
    for doi, count in list(crossref_pub.co_cited_counts.items()):
        if count >= min_count:
            dois.append(doi)

    return dois

def get_strong_citation_relationship(crossref_pub, shared):
    """
    Populate crossref_pub.strong_cit_pubs with DOIs representing strong citation relationships.

    This function:
      - Initializes crossref_pub.strong_cit_pubs as a set.
      - Adds direct references' and citations' DOIs.
      - Unions in DOIs from strongly co-citing and strongly co-cited publications.

    Args:
        crossref_pub: CrossRefPublication object to update.
        shared: float fraction used by co-citing/co-cited threshold calculations.

    Returns:
        set: Set of DOIs representing strong related publications.
    """
    strong_related_pub_dois = set()

    # Add direct references
    for reference in crossref_pub.references:
        strong_related_pub_dois.add(reference['doi'])

    # Add direct citations
    for citation in crossref_pub.citations:
        strong_related_pub_dois.add(citation.get('doi', citation.get('DOI')))

    # Add strongly co-citing publications
    strong_related_pub_dois = strong_related_pub_dois.union(get_strong_co_citing(crossref_pub, shared))

    # Add strongly co-cited publications
    strong_related_pub_dois = strong_related_pub_dois.union(get_strong_co_cited(crossref_pub, shared))

    return strong_related_pub_dois

def main():
    """
    Main entry point: load included studies, build CrossRefPublication objects,
    filter citations by year range, and compute strong citation relationships.

    Configuration values (can be modified here):
      - shared: threshold fraction for 'strong' co-citation/co-citing
      - min_year: minimum publication year for citations (inclusive), None for no lower bound
      - max_year: maximum publication year for citations (inclusive), None for no upper bound
      - review: review identifier used to locate included studies
      - studies_folder / output_folder: paths for inputs/outputs

    Note: Input file should have DOIs instead of EIDs:
      Format: Title,DOI (e.g., "Paper Title","10.1037/0003-066X.59.1.29")

    Returns:
        None
    """
    shared = 0.10
    min_year = 2010  # Minimum year (inclusive)
    max_year = 2020  # Maximum year (inclusive)
    # Use None for no bound: min_year = None  or  max_year = None

    review = 'crossref-review'
    studies_folder = 'data/included-studies'
    output_folder = 'data/crossref-download'

    print('Getting list of included studies from CrossRef...')
    seeds = []
    input_file = os.path.join(studies_folder, review, 'included.csv')

    if not os.path.exists(input_file):
        print(f'ERROR: Input file not found: {input_file}')
        print(f'Please create the file with format: Title,DOI')
        print(f'Example:')
        print(f'  "Sample Paper Title","10.1037/0003-066X.59.1.29"')
        print(f'  "Another Paper","10.1234/example.doi"')
        return

    with open(input_file) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                # Extract DOI (second column), remove quotes if present
                doi = parts[1].strip().strip('"')
                seeds.append(doi)

    print(f'Found {len(seeds)} seed publications')

    print('Getting citation space from CrossRef...')
    crossref_pubs = {}
    for seed_doi in seeds:
        print(f'  Processing: {seed_doi}')
        crossref_pubs[seed_doi] = CrossRefPublication(output_folder, seed_doi)
        crossref_pubs[seed_doi].filter_citations(min_year=min_year, max_year=max_year)

        # Display basic info
        pub = crossref_pubs[seed_doi]
        print(f'    Title: {pub.title}')
        print(f'    Year: {pub.pub_year}')
        print(f'    References: {pub.reference_count}')
        print(f'    Citation count: {pub.get_citation_count()}')

    print('\\nGetting strong citation relationships...')
    all_strong_related_dois = set()
    for seed_doi in seeds:
        strong_dois = get_strong_citation_relationship(crossref_pubs[seed_doi], shared)
        all_strong_related_dois = all_strong_related_dois.union(strong_dois)
        print(f'  {seed_doi}: {len(strong_dois)} related publications')

    print(f'\\nTotal unique related publications found: {len(all_strong_related_dois)}')

    # Save results
    output_file = os.path.join('data', 'crossref_related_dois.txt')
    os.makedirs('data', exist_ok=True)

    with open(output_file, 'w') as f:
        for doi in sorted(all_strong_related_dois):
            f.write(f'{doi}\\n')

    print(f'\\nResults saved to: {output_file}')

    # Note about limitations
    print('\\n' + '='*70)
    print('NOTE: CrossRef API Limitations')
    print('='*70)
    print('CrossRef provides:')
    print('  ✓ Full list of references (works cited)')
    print('  ✓ Citation count via is-referenced-by-count')
    print('  ✗ Full list of citing works (requires Cited-by membership)')
    print('')
    print('To get full citation data, consider:')
    print('  1. Become a CrossRef member and use Cited-by service')
    print('  2. Integrate with OpenCitations (free citation database)')
    print('  3. Use the Scopus module for complete citation networks')
    print('='*70)


if __name__ == "__main__":
    main()
