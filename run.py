import os, math, time
import csv
from crossref_publication import CrossRefPublication 
from scopus_publication import ScopusPublication
from dblp_publication import DBLPPublication
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()




def has_citations(pub, service_name: str):
    """
    Check if a publication has valid citation data.
    
    Validates that a publication object has been successfully loaded with metadata
    and contains at least one citation. References are optional.
    
    Args:
        pub: Publication object to validate
        service_name (str): Name of the data source (for logging)
        
    Returns:
        bool: True if publication has metadata and at least one citation, False otherwise
    """
    try:
        ref_count =  pub.reference_count
        cite_count = pub.citation_count
        # Does citation count need to be greater than 0?  What if no one has cited it
        if cite_count > 0 or ref_count>0:
            #print(f"Using {service_name}  (refs: {ref_count}, cites: {cite_count})")
            return True
        print(f"{service_name} missing citations/references for {pub.title}")
    except Exception as e:
        print(f"Error accessing {service_name} data for {pub.title}: {e}")
    return False


def find_publication_by_doi(doi):
    """
    Search for a publication by DOI using CrossRef.
    
    Args:
        doi (str): DOI identifier
        
    Returns:
        CrossRefPublication: CrossRefPublication object if found, None otherwise
    """
    if not doi:
        return None
        
    try:
        pub = CrossRefPublication(doi)
        if pub:
            return pub
    except Exception as e:
        print(f"** Error creating CrossRef publication for DOI {doi}: {e}")
    
    return None


def find_publication_by_eid(eid):
    """
    Search for a publication by EID using Scopus.
    
    Args:
        eid (str): Scopus EID identifier
        
    Returns:
        ScopusPublication: ScopusPublication object if found, None otherwise
    """
    if not eid:
        return None
        
    try:
        pub = ScopusPublication(eid)
        if pub:
            return pub
    except Exception as e:
        print(f"** Error creating Scopus publication for EID {eid}: {e}")
    
    return None


def find_publication_by_dblp(dblp_key):
    """
    Search for a publication by DBLP key.
    
    Args:
        dblp_key (str): DBLP key identifier
        
    Returns:
        DBLPPublication: DBLPPublication object if found, None otherwise
    """
    if not dblp_key:
        return None
        
    try:
        pub = DBLPPublication(dblp_key=dblp_key)  
        if pub:
            return pub    
    except Exception as e:
        print(f"** DBLP failed for key {dblp_key}: {e}")

    return None


def find_publication_by_title(title):
    """
    Search for a publication by title across multiple data sources.
    
    Searches DBLP and Scopus APIs for publications matching the given title.
    Returns the first result that has valid citation data.
    
    Args:
        title (str): Publication title to search for
        
    Returns:
        Publication: First matching publication with citations, or None if not found
    """
    if title:
        print(f"** Searching DBLP for: {title}")
        dblp_results = DBLPPublication.search_by_title(title, max_results=1)
        if dblp_results:
            pub_dblp = dblp_results[0]
            print(f"Found in DBLP: {pub_dblp.dblp_key}")
            return pub_dblp              
        
        print(f"** Searching Scopus for: {title}")
        pub_scopus = ScopusPublication.search_by_title(title)
        if pub_scopus and has_citations(pub_scopus, "Scopus"):
            return pub_scopus       
        else:
            print(f"** Search by title failed for Scopus or DBLP: {title}")
    
    return None

def create_publication(doi=None, eid=None, title=None):
    """
    Factory function to create a publication object from available identifiers.
    
    Attempts to locate and create a publication object using the provided identifiers,
    trying different data sources and fallback strategies. Prioritizes finding publications
    with valid citation data.
    
    Search strategy:
    1. If title provided: Search by title in DBLP and Scopus
    2. If DOI provided: Search by DOI in DBLP, CrossRef, or Scopus
    3. If EID provided: Search by EID in Scopus
    
    Args:
        doi (str, optional): DOI identifier
        eid (str, optional): Scopus EID identifier
        title (str, optional): Publication title
        
    Returns:
        Publication: Publication object if found, None otherwise
    """
    dblp = None
    
    # Define search strategies in order of priority
    search_strategies = [
        ('title', title, find_publication_by_title),
        ('doi', doi, find_publication_by_doi),
        ('eid', eid, find_publication_by_eid),
        ('dblp', dblp, find_publication_by_dblp)
    ]

    for name, value, search_func in search_strategies:
        if not value:
            continue

        print(f"** Searching by {name}: {value}")
        pub = search_func(value)

        if pub and has_citations(pub, f"search_by_{name}"):
            print(f"** Found valid publication by {name}: {value}")
            return pub
        
        # If a publication was found but had no citations,
        # try to use its identifiers for the next search strategies.
        if pub:
            if not doi and pub.doi:
                doi = pub.doi
            if not title and pub.title:
                title = pub.title
            if not dblp and isinstance(pub, DBLPPublication) and hasattr(pub, 'dblp_key'):
                dblp = pub.dblp_key
            if not eid and pub.eid:
                eid = pub.eid
    
    print(f"** No valid publication data found for DOI: {doi}, EID: {eid}, Title: {title}")
    return None

def cache_pub_metadata(pub, output_file):
    """
    Save publication metadata to a CSV file.
    
    Appends the publication's metadata (title, year, abstract, citation counts)
    to the specified CSV file. Creates the file if it doesn't exist.
    
    Args:
        pub: Publication object containing metadata to save
        output_file (str): Path to the output CSV file
        title (str, optional): Title for reference (unused, kept for compatibility)
        
    Returns:
        Publication: The same publication object passed in
    """

    print(f"  Processing DOI: {pub.doi}, title: {pub.title}")
        
    # Create file if it doesn't exist
    if not os.path.exists(output_file):
        open(output_file, 'w').close()


    if pub:
        # save information about the seed publication
        pub.append_to_csv(output_file)

        # Display basic info
        print(f"    Title: {pub.title}")
        print(f"    Year: {pub.pub_year}")
        print(f"    References: {pub.reference_count}")
        print(f"    Citation count: {pub.citation_count}")
    return pub



def read_seed_csv(input_file):
    """
    Read seed publication identifiers from a CSV file.
    
    Parses a CSV file containing seed publications for a literature review.
    Expected columns: DOI, EID, Title (at least one must be present per row).
    
    Args:
        input_file (str): Path to the CSV file containing seed publication IDs.
        
    Returns:
        list: List of tuples (doi, eid, title) for each seed publication
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
    Save a list of publication identifiers to a text file.
    
    Writes each identifier on a separate line. Creates the file if it doesn't exist.
    
    Args:
        all_related_ids (set): Set of publication identifiers (DOIs/EIDs)
        output_file (str): Path to the output text file
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
    Main workflow for building citation networks from seed publications.
    
    Process:
    1. Load seed publications from CSV file
    2. For each seed, fetch publication data and extract references/citations
    3. Save seed publication metadata to CSV
    4. Collect all unique related publication IDs
    5. Save related IDs to text file
    6. Fetch and cache metadata for all related publications
    
    Configuration is loaded from environment variables (MIN_YEAR, MAX_YEAR, REVIEW_NAME).
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
        pub = create_publication(doi=seed_doi, eid=seed_eid, title=seed_title)

        # Create a unique list of cited and referenced publications for this seed
        if pub:
            cache_pub_metadata(pub, pubs_output_file) 
            related_ids = set(pub.references + pub.citations)     
            print(f'  {seed_doi}: {len(related_ids)} related publications')

            # Create a unique list of related ids for all seeds
            all_related_ids.update(related_ids)
        time.sleep(3)  # TODO set Rate limiting


    print(f'\nTotal unique related publications: {len(all_related_ids)}')

    # Save ids of pubs related to the seed
    save_related_ids_csv(all_related_ids, related_output_file)

    for id in all_related_ids:
        # Determine if id is a DOI or EID and call appropriate function
        if id.startswith('doi:'):
            pub = find_publication_by_doi(id.replace('doi:', ''))
        elif id.startswith('2-s2.0-'):
            pub = find_publication_by_eid(id)
        else:
            # Try DOI first, then EID
            pub = find_publication_by_doi(id)
            if not pub:
                pub = find_publication_by_eid(id)
        
        if pub:
            cache_pub_metadata(pub, pubs_output_file)
        
    

if __name__ == "__main__":   
    main()

