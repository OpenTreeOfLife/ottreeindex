import psycopg2 as psy
import sqlalchemy
import datetime as dt
from sqlalchemy import (
    Table,
    Column,
    Index,
    Integer,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    )

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSON,JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import ProgrammingError

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship,
    )

Base = declarative_base()

# define tables
curator_study_table = Table('curator_study_map', Base.metadata,
    Column('study_id', String, ForeignKey('study.id'), primary_key=True),
    Column('curator_id', Integer, ForeignKey('curator.id'), primary_key=True)
    )

class Study(Base):
    __tablename__ = 'study'
    # The studyID is of the form prefix_id, so String, not Int.
    id = Column(String, primary_key=True, index=True)
    year = Column(Integer)
    data = Column(JSONB)
    #trees = relationship('Tree',backref='study')
    # many-to-many study<-->curator relationship
    curators = relationship('Curator',
        secondary=curator_study_table,
        back_populates='studies')

class Tree(Base):
    __tablename__ = 'tree'
    __table_args__ = (
        UniqueConstraint('id','study_id'),
        )
    id = Column(Integer,primary_key=True)
    tree_id = Column(String, nullable=False)
    data = Column(JSONB)
    study_id = Column(String, ForeignKey("study.id"), nullable=False)
    # # many-to-many tree<-->otu relationship
    # otus = relationship('Otu',
    #     secondary=tree_otu_table,
    #     back_populates='trees')

class Curator(Base):
    __tablename__ = 'curator'
    id = Column(Integer,primary_key=True)
    name = Column(String,nullable=False,unique=True)
    # many-to-many study<-->curator relationship
    studies = relationship('Study',
        secondary=curator_study_table,
        back_populates='curators')

# the tree queries involve joins on study table
def query_trees(session):
    property_type = '^ot:tag'
    property_value = 'ITS'

    trees = session.query(
        Tree.tree_id.label('ot:treeId'),
        Tree.study_id.label('ot:studyId'),
        Tree.data[('^ot:branchLengthMode')].label('ot:branchLengthMode'),
        Tree.data[('^ot:branchLengthDescription')].label('ot:branchLengthDescription')
    ).filter(
        Tree.data.contains({property_type:[property_value]})
    ).all()

    resultslist = []
    studydict = {}
    for row in trees:
        treedict = row._asdict()
        studyid = treedict['ot:studyId']
        if not studyid in studydict:
            # if this is the first time we have seen this study,
            # get the study properties and add a blank list for the trees
            get_study_properties(session,studyid,studydict)
            studydict[studyid]['matched_trees']=[]
        # add the tree properties to the list of matched trees
        studydict[studyid]['matched_trees'].append(treedict)
    for k,v in studydict.items():
        print "\nStudy",k
        print v
        resultslist.append(v)

def get_study_properties(session,studyid,studydict):
    slist =[
        "^ot:studyPublicationReference","^ot:curatorName",
        "^ot:studyYear","^ot:focalClade","^ot:focalCladeOTTTaxonName",
        "^ot:dataDeposit","^ot:studyPublication"
        ]
    # assigning labels like this makes it easy to build the response json
    # but can't directly access any particular item via the label,
    # i.e result.ot:studyId because of ':' in label
    query_obj = session.query(
        Study.id.label('ot:studyId'),
        Study.data[(slist[0])].label('ot:studyPublicationReference'),
        Study.data[(slist[1])].label('ot:curatorName'),
        Study.data[(slist[2])].label('ot:studyYear'),
        Study.data[(slist[3])].label('ot:focalClade'),
        Study.data[(slist[4])].label('ot:focalCladeOTTTaxonName'),
        Study.data[(slist[5])].label('ot:dataDeposit'),
        Study.data[(slist[6])].label('ot:studyPublication'),
    ).filter(
        Study.id == studyid
    )

    # should only be one row
    resultdict = {}
    for row in query_obj.all():
        for k,v in row._asdict().items():
            if v is not None:
                resultdict[k]=v
    studydict[studyid] = resultdict
    return studydict

def query_fulltext(session):
    property_type = '^ot:studyPublicationReference'
    # add wildcards to the property_value
    property_value = '%Smith%'
    study = session.query(Study).filter(
        Study.data[
            property_type
        ].astext.ilike(property_value)
    )
    print "studies with Smith in reference: ",study.count()

# methods
def basic_jsonb_query(session):
    print "basic_jsonb_query"
    # one with integer
    year = 2016
    study = session.query(Study).filter(
        Study.data[
            ('^ot:studyYear')
        ].cast(sqlalchemy.Integer) == year
        )
    print "studies with year = 2016: ",study.count()

    # one with string
    focalclade = 'Aves'
    study = session.query(Study).filter(
        Study.data[
            ('^ot:focalCladeOTTTaxonName')
        ].astext == focalclade
        )
    print "studies with focalclade=Aves: ",study.count()

    # doi, which is a path
    doi = 'http://dx.doi.org/10.1600/036364408785679851'
    study = session.query(Study).filter(
        Study.data[
            ('^ot:studyPublication','@href')
        ].astext == doi
        )
    print "studies with doi=http://dx.doi.org/10.1600/036364408785679851: ",study.count()

def test_filtering(session):
    list = ["^ot:studyYear","^ot:focalClade"]
    #for id,f,g in session.query(Study.id,Study.data[(list[0])],Study.data[(list[1])]):
    #    print id,f,g

    # test filtering
    starttime = dt.datetime.now()
    query_obj = session.query(
        Study.id.label('id'),
        Study.data[(list[0])].label('year'),
        Study.data[(list[1])].label('clade')
        )
    filtered = query_obj.filter(
        Study.data[
            ('^ot:studyYear')
            ].cast(sqlalchemy.Integer)==2016
        ).all()
    endtime = dt.datetime.now()
    #for row in filtered:
    #    for k,v in row._asdict().items():
    #        if v is not None:
    #            print '({label},{value})'.format(label=k,value=v)
    #print len(filtered)
    print "Query, then filter: ",endtime - starttime

    starttime = dt.datetime.now()
    query_obj = session.query(Study.id,Study.data[(list[0])],Study.data[(list[1])]).filter(
        Study.data[
            ('^ot:studyYear')
        ].cast(sqlalchemy.Integer)==2016
        ).all()
    endtime = dt.datetime.now()
    #print query_obj.count()
    print "Query and filter: ",endtime - starttime

def test_filter_strings(sesion):
    list = ["^ot:studyYear","^ot:focalClade"]
    # test filter strings
    query_obj = session.query(
        Study.id.label('id'),
        Study.data[(list[0])].label('year'),
        Study.data[(list[1])].label('clade')
        )
    #filter_string = "{type} = '{value}'".format(type='id',value='ot_159')
    filter_string = "Study.id = '{value}'".format(value='ot_159')
    filtered = query_obj.filter(text(filter_string))
    print filtered.count()

# def like_query(session):
#     # query.filter(User.name.like('%ed%'))
#     curatorName = "Cranston"

def value_in_array(session):
    print "testing tag query; looking for value in list"
    #tag = 'cpDNA'
    tag = 500
    property_value = [tag]
    property_type = "^ot:tag"
    searchdict = {property_type:property_value}
    studies = session.query(Study).filter(
        #Study.data.contains('{"^ot:tag":["cpDNA"]}')
        #Study.data.contains(searchdict)
        Study.data.contains({property_type:[tag]})
        )
    print "studies with tag=cpDNA",studies.count()

def test_joins(session):
    print "test_joins"
    # sqlstring: select curator_study_map.study_id
    #   from curator_study_map
    #   join curator on curator.id=curator_study_map.curator_id
    #   where curator.name='Karen Cranston';
    curatorName = 100
    query_obj = session.query(
            Study.id
        ).filter(Study.curators.any(name=curatorName))
    print "studies for {c}".format(c=curatorName)
    for row in query_obj.all():
        print row.id

    studyid = "ot_159"
    query_obj = session.query(
            Curator.name
        ).filter(Curator.studies.any(id=studyid))
    print "curators for {s}".format(s=studyid)
    for row in query_obj.all():
        print row.name


if __name__ == "__main__":
    connection_string = 'postgresql://pguser@localhost/newoti'
    db = sqlalchemy.create_engine(connection_string)
    engine = db.connect()
    meta = sqlalchemy.MetaData(engine)
    SessionFactory = sessionmaker(engine)
    session = SessionFactory()

    try:
        #test_joins(session)
        # value_in_array(session)
        # basic_jsonb_query(session)
        # query_fulltext(session)
        query_trees(session)
    except ProgrammingError as e:
        print e.message
