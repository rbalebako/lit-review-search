import os, math, time
import csv
from crossref_publication import CrossRefPublication 
from scopus_publication import ScopusPublication
from dblp_publication import DBLPPublication
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()




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
            ref_count =  pub.reference_count
            cite_count = pub.citation_count
            # Does citation count need to be greater than 0?  What if no one has cited it
            if cite_count > 0:
                print(f"Using {service_name} for {identifier} (refs: {ref_count}, cites: {cite_count})")
                return True
            print(f"{service_name} missing citations/references for {identifier}")
    except Exception as e:
        print(f"Error accessing {service_name} data for {identifier}: {e}")
    return False


def create_publication(data_folder, doi=None, eid=None, title=None):
    """
    Factory function that tries to create publications in order:
    1. DBLP (if title provided) - for computer science publications
    2. CrossRef (if DOI provided) - general academic publications
    3. Scopus (if EID provided) - as final fallback
    
    Args:
        data_folder (str): Folder for storing publication data
        doi (str, optional): DOI identifier
        eid (str, optional): EID identifier (Scopus)
        title (str, optional): Publication title for DBLP search
        
    Returns:
        Publication: Publication object or None if creation fails
    """
    
    # Try DBLP first if title is provided
    if title:
        print(f"** Searching DBLP for: {title}")
        dblp_results = DBLPPublication.search_by_title(title, data_folder, max_results=1)
        if dblp_results:
            pub = dblp_results[0]
            # Trigger metadata download
            pub.metadata
            doi = pub.doi if doi is None else doi
            if pub.title and title.lower() in pub.title.lower():
                print(f"Found in DBLP: {pub.dblp_key}")
                if validated_publication(pub, doi or eid or title, "DBLP"):
                    return pub   
                else:
                    print(f"** DBLP search did not return references '{title}': {e}")
    
    # Try CrossRef second if DOI is provided
    if doi:
        print(f"** Searching Crossref for: {doi}")
        pubcrossref = CrossRefPublication(data_folder, doi)
        if validated_publication(pubcrossref, doi, "CrossRef"):
            return pubcrossref
        else:
            print(f"** Did not find references for {doi} in Crossref")
    
    # Try Scopus as fallback if EID is provided
    if eid:
        print(f"** Searching Scopus for: {eid}")
        pubscopus = ScopusPublication(data_folder, eid)
        if validated_publication(pubscopus, eid, "Scopus"):
            return pubscopus       
        else:
            print(f"** Failed to create Scopus publication for {eid}: {e}")
    
    print(f"** No valid publication data found for DOI: {doi}, EID: {eid}, Title: {title}")
    return None


def cache_pub_metadata(seed_doi, seed_eid, output_file, title=None):
    """
    Given a seed publication identifiers, fetch and cache its metadata.
    Side effect: saves the metadata in the output_file

    Args:
        seed_doi (str): Seed publication DOI
        seed_eid (str): Seed publication EID
        output_file (str): Where to save information about the seed
        title (str, optional): Publication title for reference

    Returns:
        Publication: Publication object or None
    """

    print(f"  Processing DOI: {seed_doi}, EID: {seed_eid}")
        
    # Create file if it doesn't exist
    if not os.path.exists(output_file):
        open(output_file, 'w').close()
    pub = create_publication(output_file, doi=seed_doi, eid=seed_eid, title=title)

    if pub:
        # save information about the seed publication
        pub.append_to_csv(output_file)

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
        list: List of tuples (doi, eid, title) with seed publication data.
    """
    seeds = []
    print(f'Getting list of seed studies from {input_file}...')
    
    if not os.path.exists(input_file):
        print(f'ERROR: Input file not found: {input_file}')
        return seeds
    
    # Use csv library for parsing - simplified
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Assuming columns are named 'DOI', 'EID', and 'Title'
            doi = row.get('DOI', '').strip()
            eid = row.get('EID', '').strip()
            title = row.get('Title', '').strip()
            if doi or eid or title:
                seeds.append((doi, eid, title))
    
    return seeds

def save_related_ids_csv(all_related_ids, output_file):
    """
    Save related publication IDs to a text file.
    
    Args:
        all_related_ids (set): Set of related publication IDs to save.
        output_file (str): Full path where the output file will be saved.
    """
    
    # Create file if it doesn't exist
    if not os.path.exists(output_file):
        open(output_file, 'w').close()
    
    with open(output_file, 'w') as f:
        for id in all_related_ids:
            f.write(f'{id}\n')
    
    print(f'Results saved to: {output_file}')

def main():
    """
    Main entry point using Crossref or Scopus to build citations list from seed DOI list
    """
    # Load configuration from environment variables
    min_year = int(os.getenv('MIN_YEAR', '2022'))
    max_year = int(os.getenv('MAX_YEAR', '2025'))
    reviewname = os.getenv('REVIEW_NAME', 'firsttry')


    seeds_input_file = os.path.join(f'data/{reviewname}', 'seeds.csv')
    pubs_output_file = os.path.join(f'data/{reviewname}', 'publications.csv')
    related_output_file = os.path.join(f'data/{reviewname}', 'seed_related_ids.txt')

    seeds = read_seed_csv(seeds_input_file)
    print(f'Found {len(seeds)} seed publications')

    all_related_ids = set()
    for seed_doi, seed_eid, seed_title in seeds:
        pub = cache_pub_metadata(seed_doi, seed_eid, pubs_output_file, seed_title)

        # Create a unique list of cited and referenced publications for this seed
        if pub:
            related_ids = set(pub.references + pub.citations)     
            print(f'  {seed_doi}: {len(related_ids)} related publications')

            # Create a unique list of related ids for all seeds
            all_related_ids.update(related_ids)
        time.sleep(3)  # TODO set Rate limiting


    print(f'\nTotal unique related publications: {len(all_related_ids)}')

    # Save ids of pubs related to the seed
    save_related_ids_csv(all_related_ids, related_output_file)

    

if __name__ == "__main__":   
    main()

