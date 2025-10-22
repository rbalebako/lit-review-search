import math, os
from publication import Publication 

def get_strong_co_citing(publication, shared):
    min_count = math.ceil(publication.reference_count * shared)

    eids = []
    for eid, count in list(publication.co_citing_counts.items()):
            if count >= min_count:
                eids.append(eid)

    return eids

def get_strong_co_cited(publication, shared):
    min_count = math.ceil(publication.citation_count * shared)
    
    eids = []
    for eid, count in list(publication.co_cited_counts.items()):
        if count >= min_count:
            eids.append(eid)

    return eids

def get_strong_citation_relationship(publication, shared, store = False, overwrite = False):
    """
    Compute the set of strongly related publication IDs for a Publication.

    This function:
      - collects direct references' and citations' EIDs or DOIs,
      - adds EIDs from strong co-citing and strong co-cited publications,
      - optionally stores the resulting set to data/<eid>/top_shared.txt.

    Args:
        publication (Publication): publication to analyze.
        shared (float): threshold fraction for co-citing/co-cited decisions.
        store (bool): if True, write results to disk under data/<eid>/top_shared.txt.
        overwrite (bool): if True, overwrite existing file when storing.

    Returns:
        set[str]: set of EID strings representing strong related publications.
    """
    strong_related_pub_eids = set()

    #TODO in the Crossref version, this will be a list of DOIs with 'doi' in the name
    for reference in publication.references_:
        strong_related_pub_eids.add(reference['eid'])

    for citation in publication.citations_:
        strong_related_pub_eids.add(citation['eid'])

    strong_related_pub_eids = strong_related_pub_eids.union(get_strong_co_citing(publication, shared))
    strong_related_pub_eids = strong_related_pub_eids.union(get_strong_co_cited(publication, shared))

    if store:
        out_path = os.path.join('data', publication.eid, 'top_shared.txt')
        # create directory if needed
        out_dir = os.path.dirname(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        if overwrite or not os.path.exists(out_path):
            with open(out_path, 'w', encoding='utf-8') as o:
                for pub in strong_related_pub_eids:
                    o.write(pub)
                    o.write('\n')

    return strong_related_pub_eids