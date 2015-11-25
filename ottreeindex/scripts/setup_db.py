# Sets up the postgres database for future nexson import
# Either deletes tables and re-creates
# or simply clears all tables

import argparse
import psycopg2 as psy
import simplejson as json
from collections import defaultdict

# fill these in as they are for your system
DBNAME = 'newoti'
USER = 'pguser'
STUDYTABLE = 'study'
TREETABLE = 'tree'
CURATORTABLE='curator'
OTUTABLE='otu'
CURATORSTUDYTABLE='curator_study_map'
GININDEX='study_ix_jsondata_gin'
# tablelist ordered for DROP and TRUNCATE actions
tablelist = [
    CURATORSTUDYTABLE,
    OTUTABLE,
    CURATORTABLE,
    TREETABLE,
    STUDYTABLE,
    ]

def clear_tables(connection,cursor):
    print 'clearing tables'
    # tree linked to study via foreign key, so cascade removes both
    for table in tablelist:
        sqlstring=('TRUNCATE {name} CASCADE;'
            .format(name=table)
        )
        print '  SQL: ',cursor.mogrify(sqlstring)
        cursor.execute(sqlstring)
    # also remove the index
    sqlstring = "DROP INDEX IF EXISTS {indexname};".format(indexname=GININDEX)
    cursor.execute(sqlstring)
    connection.commit()

def connect():
    try:
        connectionstring="dbname={dbname} user={dbuser}".format(dbname=DBNAME,dbuser=USER)
        conn = psy.connect(connectionstring)
        cursor = conn.cursor()
    except KeyboardInterrupt:
        print "Shutdown requested because could not connect to DB"
    except Exception:
        traceback.print_exc(file=sys.stdout)
    return (conn,cursor)

def create_phylesystem_obj():
    # create connection to local phylesystem
    phylesystem_api_wrapper = PhylesystemAPI(get_from='local')
    phylesystem = phylesystem_api_wrapper.phylesystem_obj
    return phylesystem

def create_single_table(connection,cursor,tablename,tablestring):
    try:
        if (table_exists(cursor,tablename)):
            print '{table} exists'.format(table=tablename)
        else:
            print 'creating table',tablename
            cursor.execute(tablestring)
            connection.commit()
    except psycopg2.ProgrammingError, ex:
        fail('Error creating table {name}'.format(name=table))


# check if tables exist, and if not, create them
def create_all_tables(connection,cursor):
    # study table
    tablestring = ('CREATE TABLE {tablename} '
        '(id text PRIMARY KEY, '
        'year integer, '
        'data jsonb);'
        .format(tablename=STUDYTABLE)
        )
    create_single_table(connection,cursor,STUDYTABLE,tablestring)

    # tree table
    tablestring = ('CREATE TABLE {tablename} '
        '(id serial PRIMARY KEY, '
        'tree_id text NOT NULL, '
        'study_id text REFERENCES study (id), '
        'UNIQUE (tree_id,study_id));'
        .format(tablename=TREETABLE)
        )
    create_single_table(connection,cursor,TREETABLE,tablestring)

    # curator table
    tablestring = ('CREATE TABLE {tablename} '
        '(id serial PRIMARY KEY, '
        'name text NOT NULL);'
        .format(tablename=CURATORTABLE)
        )
    create_single_table(connection,cursor,CURATORTABLE,tablestring)

    # study-curator table
    tablestring = ('CREATE TABLE {tablename} '
        '(curator_id int REFERENCES curator (id) ,'
        'study_id text REFERENCES study (id));'
        .format(tablename=CURATORSTUDYTABLE)
        )
    create_single_table(connection,cursor,CURATORSTUDYTABLE,tablestring)

    # OTU-tree table
    tablestring = ('CREATE TABLE {tablename} '
        '(id int PRIMARY KEY, '
        'ott_name text, '
        'tree_id int REFERENCES tree (id));'
        .format(tablename=OTUTABLE)
        )
    create_single_table(connection,cursor,OTUTABLE,tablestring)

def delete_tables(connection,cursor):
    print 'deleting tables'
    try:
        for table in tablelist:
            sqlstring=('DROP TABLE IF EXISTS '
                '{name} CASCADE;'
                .format(name=table)
                )
            print '  SQL: ',cursor.mogrify(sqlstring)
            cursor.execute(sqlstring)
            connection.commit()
    except psycopg2.ProgrammingError, ex:
        fail('Error deleteting table {name}'.format(name=table))

def index_json_column(connection,cursor):
    print "creating GIN index on JSON column"
    try:
        sqlstring = ('CREATE INDEX {indexname} on {tablename} '
            'USING gin({column});'
            .format(indexname=GININDEX,tablename=STUDYTABLE,column='data'))
        cursor.execute(sqlstring)
        connection.commit()
    except psycopg2.ProgrammingError, ex:
        fail('Error creating GIN index')

def table_exists(cursor, tablename):
    sqlstring = ("SELECT EXISTS (SELECT 1 "
        "FROM information_schema.tables "
        "WHERE table_schema = 'public' "
        "AND table_name = '{0}');"
        .format(tablename)
        )
    cursor.execute(sqlstring)
    return cursor.fetchone()[0]

if __name__ == "__main__":
    # get command line argument (option to delete tables and start over)
    parser = argparse.ArgumentParser(description='set up database tables')
    parser.add_argument('-d',
        dest='delete_tables',
        action='store_true',
        default=False,
        help='use this flag to delete tables at start'
        )
    args = parser.parse_args()
    connection, cursor = connect()

    try:
        if (args.delete_tables):
            delete_tables(connection,cursor)
            create_all_tables(connection,cursor)
            index_json_column(connection,cursor)
        else:
            create_all_tables(connection,cursor)
            clear_tables(connection,cursor)
            index_json_column(connection,cursor)
    except psy.Error as e:
        print e.pgerror

    connection.close()