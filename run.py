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
        # TODO remove this hack for when the API key doesn't work
        no_api=False
        while (no_api):
            pub = ScopusPublication(data_folder, identifier)
    
            if result := check_publication_data(pub, identifier, "Scopus"):
                return result
            
    except Exception as e:
        print(f"Failed to create Scopus publication for {identifier}: {e}")
    
    print(f"No valid publication data found for {identifier}")
    return None


def get_all_related_publications(seedids, output_folder):
    """
    Given a list of seed publication IDs, return the set of all related publication IDs.
    Side effect: saves the list in the output_folder

    Args:
        seedids (list): List of seed publication IDs.
        output_fodler: Where to save information about the seedids

    Returns:
        set: Set of all related publication IDs.
    """
       
    publications = {} # list of citations and references
    all_related_ids = set()
    for seed_id in seedids:
        print(f"  Processing: {seed_id}")
        pub = create_publication(output_folder, seed_id)
        if pub:
            publications[seed_id] = pub

            # Display basic info
            print(f"    Title: {pub.title}")
            print(f"    Year: {pub.pub_year}")
            print(f"    References: {pub.reference_count}")
            print(f"    Citation count: {pub.get_citation_count()}")

            # Create a unique list of cited and referenced publications for this seed
            related_ids = set(pub.references + pub.citations)     
        
            print(f'  {seed_id}: {len(related_ids)} related publications')

            # Create a unique list of related ids for all seeds
            all_related_ids.update(related_ids)
            time.sleep(1)  # TODO set Rate limiting
    

    return all_related_ids



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


    print('Getting list of seed studies...')
    seeds = []
    input_file = os.path.join(studies_folder, reviewname, 'included.csv')

    if not os.path.exists(input_file):
        print(f'ERROR: Input file not found: {input_file}')
        return

    # Use csv library for parsing
    with open(input_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header row
        for row in reader:
            if len(row) >= 3:
                id = row[2].strip().strip('"')
                if id:
                    seeds.append(id)

    print(f'Found {len(seeds)} seed publications')

    all_related_ids = get_all_related_publications(seeds, output_folder)
    print(f'\nTotal unique related publications: {len(all_related_ids)}')

    # Save results
    # TODO the path is not specific to the run, so we will want it eventuallly to be in a subfolder of
    output_file = os.path.join('data',  'crossref_related_dois.txt')
    os.makedirs('data', exist_ok=True)

    with open(output_file, 'w') as f:
        for id in all_related_ids:
            f.write(f'{id}\n')
        print(f'\nResults saved to: {output_file}')

    

if __name__ == "__main__":   
    main()

