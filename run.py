import os, math, time
import csv
from crossref_publication import CrossRefPublication 
from scopus_publication import ScopusPublication
from dblp_publication import DBLPPublication
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()




def has_citations(pub,  service_name: str):
    """

    Validate publication data for citation analysis.

    This helper function checks if a publication object contains valid citation data
    by verifying the presence of both references and citations.

    Args:
        pub: Publication object to validate. Should have 'metadata', 'references', 
             and 'citations' attributes.
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
                #print(f"Using {service_name}  (refs: {ref_count}, cites: {cite_count})")
                return True
            print(f"{service_name} missing citations/references for {pub.title}")
    except Exception as e:
        print(f"Error accessing {service_name} data for {pub.title}: {e}")
    return False


def find_publication_by_id(data_folder, id):
    """
    Search for a publication by id in DBLP and Scopus.
    
    Args:
        data_folder (str): Folder for storing publication data
        id (str): ID identifier to search for
        
    Returns:
        Publication: ScopusPublication object if found and has citations, None otherwise
    """
    if not id:
        return None
        
    try:
        pub = DBLPPublication(data_folder, id)  
        if pub:
            return pub    
        else:
            pub = ScopusPublication(data_folder, id)
            if pub:
                return pub        
    except Exception as e:
        print(f"** Error creating  publication for ID {id}: {e}")
    
    return None


def find_publication_by_title(data_folder, title):
      # Try DBLP and Scopus first if title is provided
    if title:
        print(f"** Searching DBLP for: {title}")
        dblp_results = DBLPPublication.search_by_title(title, data_folder, max_results=1)
        if dblp_results:
            pub_dblp = dblp_results[0]
            # Trigger metadata download
            pub_dblp.metadata
            # Extract DOI and EID from DBLP if not already provided
            doi = pub_dblp.doi if doi is None else doi
            eid = pub_dblp.eid if eid is None else eid
            if pub_dblp.title and title.lower() in pub_dblp.title.lower():
                print(f"Found in DBLP: {pub_dblp.dblp_key}")
                if has_citations(pub_dblp, "DBLP"):
                    return pub_dblp   
                else:
                    print(f"** DBLP search did not return references for '{title}'")
        
        print(f"** Searching Scopus for: {title}")
        pub_scopus = ScopusPublication.search_by_title(title, data_folder)
        if pub_scopus and has_citations(pub_scopus, "Scopus"):
            return pub_scopus       
        else:
            print(f"** Failed to create Scopus publication for title: {title}")

    

def create_publication(data_folder, doi=None, eid=None, title=None):
    """
    Factory function that tries to create publications in order based on the data available
    TODO(maybe we can check the format of the id to see which one it is?)
    
    Args:
        data_folder (str): Folder for storing publication data
        doi (str, optional): DOI identifier
        eid (str, optional): EID identifier (Scopus)
        title (str, optional): Publication title for DBLP search
        
    Returns:
        Publication: Publication object or None if creation fails
    """
  
    while (!has_citations(pub)):
        if doi:
            pub = find_publication_by_id(data_folder, doi)
            title = pub.title
        if eid:
            pub = find_publication_by_id(data_folder, eid)
            title = pub.title
        if title
            pub_by_eid = find_publication_by_title(data_folder, title )    
            doi = pub.doi
        
    if not pub:
        print(f"** No valid publication data found for DOI: {doi}, EID: {eid}, Title: {title}")
        return None
    
    else:
       pub.has_citations()

    return pub

def cache_pub_metadata(pub, output_file, title=None):
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
        pub = create_publication(pubs_output_file, doi=seed_doi, eid=seed_eid, title=seed_title)

        # Create a unique list of cited and referenced publications for this seed
        if pub:
            cache_pub_metadata(pub) 
            related_ids = set(pub.references + pub.citations)     
            print(f'  {seed_doi}: {len(related_ids)} related publications')

            # Create a unique list of related ids for all seeds
            all_related_ids.update(related_ids)
        time.sleep(3)  # TODO set Rate limiting


    print(f'\nTotal unique related publications: {len(all_related_ids)}')

    # Save ids of pubs related to the seed
    save_related_ids_csv(all_related_ids, related_output_file)

    for (id in all_related_ids):
        pub = find_publication_by_id(id)
        if pub:
            cache_pub_metadata(pub)
        
    

if __name__ == "__main__":   
    main()

