import sys, os, math, time
from crossref_publication import CrossRefPublication 
from publication import Citation
from scopus_publication import ScopusPublication
from dotenv import load_dotenv
from requests import get
from dataclasses import dataclass


from dotenv import load_dotenv


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



def check_publication_data(pub, identifier: str, service_name: str):
    """Helper to check if a publication has valid citation data"""
    try:
        if hasattr(pub, 'metadata') and pub.metadata:  # Check metadata if exists
            ref_count = len(pub.references)
            cite_count = len(pub.citations)
            if ref_count > 0 and cite_count > 0:
                print(f"Using {service_name} for {identifier} (refs: {ref_count}, cites: {cite_count})")
                return pub
            print(f"{service_name} missing citations/references for {identifier}")
    except Exception as e:
        print(f"Error accessing {service_name} data for {identifier}: {e}")
    return None

def create_publication(data_folder, identifier):
    """Factory function that tries to create a CrossRef publication first,
    falls back to Scopus if that fails or if CrossRef has no references/citations."""
    
    # Try CrossRef first
    try:
        pub = CrossRefPublication(data_folder, identifier)
        if result := check_publication_data(pub, identifier, "CrossRef"):
            return result
    except Exception as e:
        print(f"Failed to create CrossRef publication for {identifier}: {e}")
    
    # Try Scopus as fallback
    try:
        pub = ScopusPublication(data_folder, identifier)
        if result := check_publication_data(pub, identifier, "Scopus"):
            return result
    except Exception as e:
        print(f"Failed to create Scopus publication for {identifier}: {e}")
    
    print(f"No valid publication data found for {identifier}")
    return None

def main():
    """
    Main entry point using Crossref or Scopus to build citations list from seed DOI list
    """
    shared = 0.10
    # TODO either get these values from .env or here, but don't have them in bothe placese
    min_year = 2022
    max_year = 2025

    # TODO find a more obvious place or prompt the user for this
    review = 'firsttry'
    studies_folder = 'data/included-studies'
    output_folder = 'data/crossref-download'

    print('Getting list of included studies...')
    seeds = []
    input_file = os.path.join(studies_folder, review, 'included.csv')

    if not os.path.exists(input_file):
        print(f'ERROR: Input file not found: {input_file}')
        return

    with open(input_file) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                doi = parts[2].strip().strip('"')
                if doi:
                    seeds.append(doi)

    print(f'Found {len(seeds)} seed publications')
    
    print('Getting citation space...')
    publications = {}
    for seed_doi in seeds:
        print(f"  Processing: {seed_doi}")
        pub = create_publication(output_folder, seed_doi)
        if pub:
            publications[seed_doi] = pub
            
            # Display basic info
            print(f"    Title: {pub.title}")
            print(f"    Year: {pub.pub_year}")
            print(f"    References: {pub.reference_count}")
            print(f"    Citation count: {pub.get_citation_count()}")
            
            time.sleep(1)  # Rate limiting
    
    all_related_dois = set()
    for seed_doi, pub in publications.items():
        related_dois = set()
        
        # Add references within year range
        for ref in pub.references:
            if ref and isinstance(ref, Citation):
                if ref.year and min_year <= ref.year <= max_year:
                    related_dois.add(ref.doi)

        
        # Add citations within year range
        for cite in pub.citations:
            if cite and isinstance(cite, Citation):
                related_dois.add(cite.doi)

        all_related_dois.update(related_dois)
        print(f'  {seed_doi}: {len(related_dois)} related publications')

    print(f'\nTotal unique related publications: {len(all_related_dois)}')

    # Save results
    output_file = os.path.join('data', 'crossref_related_dois.txt')
    os.makedirs('data', exist_ok=True)

    with open(output_file, 'w') as f:
        for doi in all_related_dois:
            f.write(f'{doi}\n')
        print(f'\nResults saved to: {output_file}')

if __name__ == "__main__":   
    main()

