# miscellaneous helper functions for views
# includes query functions

from .models import (
    DBSession,
    Study,
    Tree,
    Curator,
    Otu,
    )

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSON,JSONB
from sqlalchemy import Integer
from pyramid.httpexceptions import exception_response

# get all studies, no filtering
def get_all_studies(verbose):
    print "get_all_studies"
    resultlist = []
    query_obj = get_study_query_object(verbose)
    # get results as dict, where keys are the labels set in
    # get_study_query_object
    for row in query_obj.all():
        item = {}
        for k,v in row._asdict().items():
            item[k]=v
        resultlist.append(item)
    return resultlist

# get the list of searchable properties
# currently returns the v3 list only
def get_property_list(version=3):
    tree_props= [
        "ot:treebaseOTUId", "ot:nodeLabelMode", "ot:originalLabel",
        "oti_tree_id", "ot:ottTaxonName", "ot:inferenceMethod", "ot:tag",
        "ot:comment", "ot:treebaseTreeId", "ot:branchLengthDescription",
        "ot:treeModified", "ot:studyId", "ot:branchLengthTimeUnits",
        "ot:ottId", "ot:branchLengthMode", "ot:treeLastEdited",
        "ot:nodeLabelDescription"
        ]
    study_props = [
        "ot:studyModified", "ot:focalClade", "ot:focalCladeOTTTaxonName",
        "ot:focalCladeOTTId", "ot:studyPublication", "ot:studyLastEditor",
        "ot:tag", "ot:focalCladeTaxonName", "ot:comment", "ot:studyLabel",
        "ot:authorContributed", "ot:studyPublicationReference", "ot:studyId",
        "ot:curatorName", "ot:studyYear", "ot:studyUploaded", "ot:dataDeposit"
        ]
    results = {
        "tree_properties" : tree_props,
        "study_properties" : study_props
        }
    return results

# return the query object without any filtering
# (query not yet executed)
def get_study_query_object(verbose):
    query_obj = None
    if (verbose):
        clist =[
            "^ot:studyPublicationReference","^ot:curatorName",
            "^ot:studyYear","^ot:focalClade","^ot:focalCladeOTTTaxonName",
            "^ot:dataDeposit","^ot:studyPublication","^ot:tag"
            ]
        # assigning labels like this makes it easy to build the response json
        # but can't directly access any particular item via the label,
        # i.e result.ot:studyId because of ':' in label
        query_obj = DBSession.query(
            Study.id.label('ot:studyId'),
            Study.data[(clist[0])].label('ot:studyPublicationReference'),
            Study.data[(clist[1])].label('ot:curatorName'),
            Study.data[(clist[2])].label('ot:studyYear'),
            Study.data[(clist[3])].label('ot:focalClade'),
            Study.data[(clist[4])].label('ot:focalCladeOTTTaxonName'),
            Study.data[(clist[5])].label('ot:dataDeposit'),
            Study.data[(clist[6])].label('ot:studyPublication'),
            Study.data[(clist[7])].label('ot:tag'),
        )
    else:
        query_obj = DBSession.query(Study.id.label('ot:studyId'))
    return query_obj

# find studies curated by a particular user
def query_studies_by_curator(query_obj,property_value):
    curatorName = property_value
    # check this is a string
    if isinstance(s, str):
        filtered = query_obj.filter(
            Study.curators.any(name=curatorName)
            )
        return filtered
    else:
        return exception_response(400)

# filter query to return only studies that match property_type and
# property_value
def query_studies(verbose,property_type,property_value):
    resultlist = []
    query_obj = get_study_query_object(verbose)
    filtered = None
    # vastly different queries for different property types

    # study id is straightforward
    if property_type == "ot:studyId":
        filtered = query_obj.filter(Study.id == property_value)

    # curator uses study-curator association table
    elif property_type == "ot:curator":
        filtered = query_studies_by_curator(query_obj,property_value)

    # year and focal clade are in json, need to cast value to int
    elif property_type == "ot:studyYear" or property_type == "ot:focalClade":
        # need to cast these value to Integer
        property_type = '^'+property_type
        filtered = query_obj.filter(
            Study.data[
                (property_type)
            ].cast(sqlalchemy.Integer) == property_value
            )

    # all other property types are strings contained in json
    else:
        property_type = '^'+property_type
        filtered = query_obj.filter(
            Study.data[
                (property_type)
            ] == property_value
            )

    # get results as dict, where keys are the labels set in
    # get_study_query_object
    for row in filtered.all():
        item = {}
        for k,v in row._asdict().items():
            item[k]=v
        resultlist.append(item)
    return resultlist