import os, math, time
import csv
from crossref_publication import CrossRefPublication 
from scopus_publication import ScopusPublication




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



def validated_publication(pub, identifier: str, service_name: str):
    """

    Validate publication data for citation analysis.

    This helper function checks if a publication object contains valid citation data
    by verifying the presence of both references and citations.

    Args:
        pub: Publication object to validate. Should have 'metadata', 'references', 
             and 'citations' attributes.
        identifier (str): Unique identifier for the publication (e.g., DOI, PubMed ID).
        service_name (str): Name of the service providing the publication data 
                           (used for logging purposes).

    Returns:
        object or None: Returns the publication object if it has valid citation data
                       (both references and citations present with count > 0), 
                       otherwise returns None.
        
    """
    try:
        if hasattr(pub, 'metadata') and pub.metadata:  # Check metadata if exists
            ref_count = len(pub.references)
            cite_count = len(pub.citations)
            if ref_count > 0 and cite_count > 0:
                print(f"Using {service_name} for {identifier} (refs: {ref_count}, cites: {cite_count})")
                return True
            print(f"{service_name} missing citations/references for {identifier}")
    except Exception as e:
        print(f"Error accessing {service_name} data for {identifier}: {e}")
    return False


def create_publication(data_folder, identifier):
    """Factory function that tries to create a CrossRef publication first,
    falls back to Scopus if that fails or if CrossRef has no references/citations."""
    
    # Try CrossRef first
    try:
        pub = CrossRefPublication(data_folder, identifier)
        if validated_publication(pub, identifier, "CrossRef"):
            return pub
    except Exception as e:
        print(f"Failed to create CrossRef publication for {identifier}: {e}")
    
    # Try Scopus as fallback
    try:
        # TODO remove this hack for when the API key doesn't work
        no_api=False
        while (no_api):
            pub = ScopusPublication(data_folder, identifier)
    
            if validated_publication(pub, identifier, "Scopus"):
                return pub       
    except Exception as e:
        print(f"Failed to create Scopus publication for {identifier}: {e}")
    
    print(f"No valid publication data found for {identifier}")
    return None


def cache_pub_metadata(seed_id, output_folder):
    """
    Given a list of seed publication IDs, return the set of all related publication IDs.
    Side effect: saves the list in the output_folder

    Args:
        seedids (list): List of seed publication IDs.
        output_fodler: Where to save information about the seedids

    Returns:
        set: Set of all related publication IDs.
    """

    print(f"  Processing: {seed_id}")
    pub = create_publication(output_folder, seed_id)

    if pub:
        # save information about the seed publication
        pub.append_to_csv('output/publications.csv')

        # Display basic info
        print(f"    Title: {pub.title}")
        print(f"    Year: {pub.pub_year}")
        print(f"    References: {pub.reference_count}")
        print(f"    Citation count: {pub.get_citation_count()}")
    return pub



def read_seed_csv(input_file):
    """
    Read seed publication IDs from a CSV file.
    
    Args:
        input_file (str): Path to the CSV file containing seed publication IDs.
        
    Returns:
        list: List of seed publication IDs (DOI or ID values from CSV).
    """
    seeds = []
    
    if not os.path.exists(input_file):
        print(f'ERROR: Input file not found: {input_file}')
        return seeds
    
    # Use csv library for parsing - simplified
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Assuming third column is named 'DOI' or 'ID'
            # Adjust key name based on your CSV header
            id = row.get('DOI', '').strip() or row.get('ID', '').strip()
            if id:
                seeds.append(id)
    
    return seeds

def save_related_ids_csv(all_related_ids, output_folder):
    """
    Save related publication IDs to a text file.
    
    Args:
        all_related_ids (set): Set of related publication IDs to save.
        output_folder (str): Directory where the output file will be saved.
    """
    output_file = os.path.join(output_folder, 'seed_related_ids.txt')
    os.makedirs(output_folder, exist_ok=True)

    with open(output_file, 'w') as f:
        for id in all_related_ids:
            f.write(f'{id}\n')
    
    print(f'Results saved to: {output_file}')

def main():
    """
    Main entry point using Crossref or Scopus to build citations list from seed DOI list
    """
    shared = 0.10
    # TODO either get these values from .env or here, but don't have them in both places
    min_year = 2022
    max_year = 2025

    # TODO find a more obvious place or prompt the user for this
    reviewname = 'firsttry'
    studies_folder = f'data/{reviewname}/seed-studies'
    output_folder = f'data/{reviewname}/related-ids'
    input_file = os.path.join(studies_folder, reviewname, 'included.csv')


    print('Getting list of seed studies...')
    seeds = read_seed_csv(input_file)
    print(f'Found {len(seeds)} seed publications')

    all_related_ids = set()
    for seed_id in seeds:
        pub = cache_pub_metadata(seeds, output_folder)

        # Create a unique list of cited and referenced publications for this seed
        related_ids = set(pub.references + pub.citations)     
        print(f'  {seed_id}: {len(related_ids)} related publications')

        # Create a unique list of related ids for all seeds
        all_related_ids.update(related_ids)
        time.sleep(3)  # TODO set Rate limiting


    print(f'\nTotal unique related publications: {len(all_related_ids)}')

    # Save ids of pubs related to the seed
    save_related_ids_csv(all_related_ids, output_folder)

if __name__ == "__main__":   
    main()

