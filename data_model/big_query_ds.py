# Imports
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from google.cloud import bigquery
from google.cloud import storage
import pandas as pd
import requests
import logging
import time
import os


# Set up logging
logging.basicConfig(level=logging.INFO,
                     format='%(asctime)s - %(levelname)s - %(message)s',
                     datefmt='%Y-%m-%d %H:%M:%S')

PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT') 
logging.info('Google Cloud project is {}'.format(PROJECT))


# Initialisation
logging.info('Initialising BigQuery client')
BQ_CLIENT = bigquery.Client()

BUCKET_NAME = PROJECT + '.appspot.com'
logging.info('Initialising access to storage bucket {}'.format(BUCKET_NAME))
APP_BUCKET = storage.Client().bucket(BUCKET_NAME)

logging.info('Initialisation complete')


# Upload .csv files to bucket to define BigQuery dataset
def uploadFilesToBucket():
    blob = APP_BUCKET.blob("classes.csv")
    blob.upload_from_filename("classes.csv")
    blob.make_public()

    blob = APP_BUCKET.blob("image-labels.csv")
    blob.upload_from_filename("image-labels.csv")
    blob.make_public()

    blob = APP_BUCKET.blob("relations.csv")
    blob.upload_from_filename("relations.csv")
    blob.make_public()


def createClassesTable(dataset_name, cl):
    # Create classes table
    classes = dataset_name + '.cl'
    print('Creating table ' + classes)

    # Delete the table in case you're running this for the second time
    BQ_CLIENT.delete_table(classes, not_found_ok=True)

    # Create the table
    # We use the same field names as in the original data set
    table_classes = bigquery.Table(classes)
    table_classes.schema = (
        bigquery.SchemaField('Label',            'STRING'),
        bigquery.SchemaField('Description',      'STRING')
    )
    BQ_CLIENT.create_table(table_classes)

    # Insert data
    print('Loading data into ' + classes)
    load_job = BQ_CLIENT.load_table_from_dataframe(cl, table_classes)

    while load_job.running():
        print('waiting for the load job to complete')
        time.sleep(1)

    if load_job.errors == None:
        print('Load complete!')
    else:
        print(load_job.errors)



def createImgLabTable(dataset_name, im_lab):
    # Create image-labels table
    image_labels = dataset_name + '.im_lab'
    print('Creating table ' + image_labels)

    # Delete the table in case you're running this for the second time
    BQ_CLIENT.delete_table(image_labels, not_found_ok=True)

    # Create the table
    table_labels = bigquery.Table(image_labels)
    table_labels.schema = (
        bigquery.SchemaField('ImageId',  'STRING'),
        bigquery.SchemaField('Label',   'STRING')
    )
    BQ_CLIENT.create_table(table_labels)

    # Insert data
    print('Loading data into ' + image_labels)
    load_job = BQ_CLIENT.load_table_from_dataframe(im_lab, table_labels)

    while load_job.running():
        print('waiting for the load job to complete')
        time.sleep(1)

    if load_job.errors == None:
        print('Load complete!')
    else:
        print(load_job.errors)


def createRelationsTable(dataset_name, rel):
    relations = dataset_name + '.rel'
    print('Creating table ' + relations)

    # Delete the table in case you're running this for the second time
    BQ_CLIENT.delete_table(relations, not_found_ok=True)

    # Create the table
    table_relations = bigquery.Table(relations)
    table_relations.schema = (
        bigquery.SchemaField('ImageId',  'STRING'),
        bigquery.SchemaField('Label1',   'STRING'),
        bigquery.SchemaField('Relation', 'STRING'),
        bigquery.SchemaField('Label2',   'STRING')
    )
    BQ_CLIENT.create_table(table_relations)

    # Insert data
    print('Loading data into ' + relations)
    load_job = BQ_CLIENT.load_table_from_dataframe(rel, table_relations)

    while load_job.running():
        print('waiting for the load job to complete')
        time.sleep(1)

    if load_job.errors == None:
        print('Load complete!')
    else:
        print(load_job.errors)


if __name__ == '__main__':
    # Create dataset
    dataset_name = PROJECT + ".openimages"
    dataset = BQ_CLIENT.create_dataset(dataset_name, exists_ok=True)

    uploadFilesToBucket()

    # Read .csv files to define BigQuery dataset
    cl = pd.read_csv('gs://{}/classes.csv'.format(BUCKET_NAME))
    im_lab = pd.read_csv('gs://{}/image-labels.csv'.format(BUCKET_NAME))
    rel = pd.read_csv('gs://{}/relations.csv'.format(BUCKET_NAME))

    createClassesTable(dataset_name, cl)
    createImgLabTable(dataset_name, im_lab)
    createRelationsTable(dataset_name, rel)