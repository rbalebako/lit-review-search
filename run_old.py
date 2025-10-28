import sys, os, math

# Prefer CrossRefPublication; fall back to ScopusPublication if CrossRef module not available
USING_CROSSREF = False
try:
    from crossref_publication import CrossRefPublication as Publication
    USING_CROSSREF = True
    print("Defaulting to CrossRefPublication backend")
except Exception:
    try:
        from scopus_publication import ScopusPublication as Publication
        print("CrossRef backend not available — using ScopusPublication backend")
    except Exception:
        raise ImportError("Neither crossref_publication nor scopus_publication modules are importable")

def get_strong_co_citing(publication, shared):
    """
    Return EIDs of publications that are strongly co-citing with the given publication.

    Args:
        publication: Publication-like object whose co-citing counts are examined.
        shared: float fraction used to compute the minimum shared reference threshold.

    Returns:
        List of EID strings for publications with co-citing counts >= threshold.
    """
    min_count = math.ceil(publication.reference_count * shared)

    eids = []
    for eid, count in list(publication.co_citing_counts.items()):
            if count >= min_count:
                eids.append(eid)

    return eids

def get_strong_co_cited(publication, shared):
    """
    Return IDs of publications that are strongly co-cited with the given publication.

    Args:
        publication: Publication-like object whose co-cited counts are examined.
        shared: float fraction used to compute the minimum shared citation threshold.

    Returns:
        List of EID strings for publications with co-cited counts >= threshold.
    """
    min_count = math.ceil(publication.citation_count * shared)
    
    eids = []
    for eid, count in list(publication.co_cited_counts.items()):
        if count >= min_count:
            eids.append(eid)

    return eids

def get_strong_citation_relationship(publication, shared):
    """
    Populate scopus_pub.strong_cit_pubs with EIDs representing strong citation relationships.

    This function:
      - Initializes scopus_pub.strong_cit_pubs as a set.
      - Adds direct references' and citations' EIDs.
      - Unions in EIDs from strongly co-citing and strongly co-cited publications
        (as computed by get_strong_co_citing and get_strong_co_cited).

    Args:
        publication: Publication-like object to update.
        shared: float fraction used by co-citing/co-cited threshold calculations.

    Returns:
        None (updates scopus_pub in place).
    """
    publication.strong_cit_pubs = set()

    for reference in publication.references_:
        publication.strong_cit_pubs.add(reference.get('eid') or reference.get('doi'))

    for citation in publication.citations_:
        publication.strong_cit_pubs.add(citation.get('eid') or citation.get('doi'))

    # ensure the results of co-citing/co-cited are added to the set
    publication.strong_cit_pubs.update(get_strong_co_citing(publication, shared))
    publication.strong_cit_pubs.update(get_strong_co_cited(publication, shared))

    # with open(os.path.join('data', eid, 'top_shared_' + str(top) + '_' + citation_type + '.txt'), 'w') as o:
    #     for top_pub in top_pubs:
    #         o.write(top_pub)
    #         o.write('\n')

def main():
    """
    Main entry point: load included studies, build Publication objects,
    filter citations by year range, and compute strong citation relationships.

    Configuration values (can be modified here):
      - shared: threshold fraction for 'strong' co-citation/co-citing
      - min_year: minimum publication year for citations (inclusive), None for no lower bound
      - max_year: maximum publication year for citations (inclusive), None for no upper bound
      - review: review identifier used to locate included studies
      - studies_folder / output_folder: paths for inputs/outputs

    Returns:
        None
    """
    shared = 0.10
    min_year = 2022  # Minimum year (inclusive)
    max_year = 2025  # Maximum year (inclusive)
    # Use None for no bound: min_year = None  or  max_year = None

    review = 'firsttry'
    studies_folder = 'data/included-studies'
    output_folder = 'data/scopus-download'

    print('Getting list of included studies..')
    seeds = []
    with open(os.path.join(studies_folder, review, 'included.csv')) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                # Extract EID (second column), remove quotes if present
                eid = parts[1].strip().strip('"')
                seeds.append(eid)

    print('Getting citation space..')
    scopus_pubs = {}
    for seed in seeds:
        # Instantiate the selected Publication class (CrossRefPublication or ScopusPublication)
        scopus_pubs[seed] = Publication(output_folder, seed)
        scopus_pubs[seed].filter_citations(min_year=min_year, max_year=max_year)

    print('Getting strong citation relationships..')
    for seed in seeds:
        get_strong_citation_relationship(scopus_pubs[seed], shared)



if __name__ == "__main__":
    main()