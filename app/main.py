# Imports
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


import flask
import logging
import os
import tfmodel
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import vision
from google.cloud import firestore


# Set up logging
logging.basicConfig(level=logging.INFO,
                     format='%(asctime)s - %(levelname)s - %(message)s',
                     datefmt='%Y-%m-%d %H:%M:%S')

PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT','bdcc-project-1-417816') 
logging.info('Google Cloud project is {}'.format(PROJECT))

# Initialisation
logging.info('Initialising app')
app = flask.Flask(__name__)

logging.info('Initialising BigQuery client')
BQ_CLIENT = bigquery.Client()

BUCKET_NAME = PROJECT + '.appspot.com'
logging.info('Initialising access to storage bucket {}'.format(BUCKET_NAME))
APP_BUCKET = storage.Client().bucket(BUCKET_NAME)

logging.info("Initialising CloudVisionAPI client")
CV_CLIENT = vision.ImageAnnotatorClient()

logging.info('Initialising TensorFlow classifier')
TF_CLASSIFIER = tfmodel.Model(
    app.root_path + "/static/tflite/model.tflite",
    app.root_path + "/static/tflite/dict.txt"
)

db = firestore.Client(project=PROJECT)

logging.info('Initialisation complete')


# End-point implementation
@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/classes')
def classes():
    results = BQ_CLIENT.query(
    '''
        Select Description, COUNT(*) AS NumImages
        FROM `bdcc-project-1-417816.openimages.im_lab`
            INNER JOIN `bdcc-project-1-417816.openimages.cl` USING(Label)
        GROUP BY Description
        ORDER BY Description
    ''').result()
    logging.info('classes: results={}'.format(results.total_rows))
    data = dict(results=results)
    return flask.render_template('classes.html', data=data)


@app.route('/relations')
def relations():
    results = BQ_CLIENT.query(
    '''
        Select Relation, COUNT(*) AS ImageCount
        FROM `bdcc-project-1-417816.openimages.rel`
        GROUP BY Relation
        ORDER BY Relation
    ''').result()
    logging.info('relations: results={}'.format(results.total_rows))
    data = dict(results=results)
    return flask.render_template('relations.html', data=data)


@app.route('/image_info')
def image_info():
    image_id = flask.request.args.get('image_id')

    classes = BQ_CLIENT.query(
    '''
        Select Description
        FROM `bdcc-project-1-417816.openimages.im_lab` AS iml
            INNER JOIN `bdcc-project-1-417816.openimages.cl` USING(Label)
        WHERE iml.ImageId = '{}'
        ORDER BY Description
    '''.format(image_id)).result()

    relations = BQ_CLIENT.query(
    '''
        Select cl1.Description, rel.Relation, cl2.Description
        FROM `bdcc-project-1-417816.openimages.im_lab` AS iml
            INNER JOIN `bdcc-project-1-417816.openimages.cl` AS cl1
                ON iml.Label = cl1.Label
            INNER JOIN `bdcc-project-1-417816.openimages.rel` AS rel
                ON cl1.Label = rel.Label1 AND iml.ImageId = rel.ImageId
            INNER JOIN `bdcc-project-1-417816.openimages.cl` AS cl2
                ON cl2.Label = rel.Label2
        WHERE iml.ImageId = '{}' AND (cl1.Description IS NOT NULL AND cl2.Description IS NOT NULL)
        ORDER BY rel.Relation
    '''.format(image_id)).result()

    logging.info('image_info: classes={}'.format(classes.total_rows))
    logging.info('image_info: relations={}'.format(relations.total_rows))

    data_classes = dict(classes=classes)
    data_relations = dict(relations=relations)
    return flask.render_template('image_info.html', image_id=image_id, data_classes=data_classes, data_relations=data_relations)


@app.route('/image_search')
def image_search():
    description = flask.request.args.get('description', default='')
    image_limit = flask.request.args.get('image_limit', default=10, type=int)
    results = BQ_CLIENT.query(
    '''
        Select ImageId
        FROM `bdcc-project-1-417816.openimages.im_lab` AS iml
            INNER JOIN `bdcc-project-1-417816.openimages.cl` AS cl
                ON iml.Label = cl.Label
        WHERE Description = '{}'
        LIMIT {}
    '''.format(description, image_limit)).result()

    logging.info('image_search: results={}'.format(results.total_rows))
    data = dict(results=results)
    return flask.render_template('image_search.html', description=description, 
                                  image_limit=image_limit, results_count = results.total_rows, data=data)


@app.route('/relation_search')
def relation_search():
    class1 = flask.request.args.get('class1', default='%')
    relation = flask.request.args.get('relation', default='%')
    class2 = flask.request.args.get('class2', default='%')
    image_limit = flask.request.args.get('image_limit', default=10, type=int)
    
    results = BQ_CLIENT.query(
    '''
        Select ImageId, cl1.Description, rl.Relation, cl2.Description
        FROM `bdcc-project-1-417816.openimages.rel` AS rl
            INNER JOIN `bdcc-project-1-417816.openimages.cl` AS cl1
                ON rl.Label1 = cl1.Label
            INNER JOIN `bdcc-project-1-417816.openimages.cl` AS cl2
                ON rl.Label2 = cl2.Label
        WHERE 
            cl1.Description LIKE '%{}%' AND
            rl.Relation LIKE '%{}%' AND
            cl2.Description LIKE '%{}%'
        ORDER BY ImageId
        LIMIT {}
    '''.format(class1, relation, class2, image_limit)).result()

    logging.info('relation_search: results={}'.format(results.total_rows))
    data = dict(results=results)
    return flask.render_template('relation_search.html', class1=class1, relation=relation, class2=class2, 
                                  image_limit=image_limit, results_count = results.total_rows, data=data)


@app.route('/image_classify_classes')
def image_classify_classes():
    with open(app.root_path + "/static/tflite/dict.txt", 'r') as f:
        data = dict(results=sorted(list(f)))
        return flask.render_template('image_classify_classes.html', data=data)
 

@app.route('/image_classify', methods=['POST'])
def image_classify():
    files = flask.request.files.getlist('files')
    min_confidence = flask.request.form.get('min_confidence', default=0.25, type=float)
    results = []
    
    if len(files) > 1 or files[0].filename != '':
        for file in files:
            classifications = TF_CLASSIFIER.classify(file, min_confidence)
            blob = storage.Blob(file.filename, APP_BUCKET)
            blob.upload_from_file(file, blob, content_type=file.mimetype)
            blob.make_public()
           
            logging.info('image_classify: filename={} blob={} classifications={}'\
                .format(file.filename,blob.name,classifications))
            results.append(dict(bucket=APP_BUCKET,
                                filename=file.filename,
                                classifications=classifications))
                        
            doc_ref = db.collection('image_classify_results').document()
            doc_ref.set({
                'filename': file.filename,
                'classifications': classifications,
            })
    
    data = dict(bucket_name=APP_BUCKET.name, 
                min_confidence=min_confidence, 
                results=results)
    return flask.render_template('image_classify.html', data=data)


@app.route('/image_classify_cloud_vision_api', methods=['POST'])
def image_classify_cloud_vision_api():
    files = flask.request.files.getlist('files')
    min_confidence = flask.request.form.get('min_confidence', default=0.25, type=float)
    results = []
    
    if len(files) > 1 or files[0].filename != '':
        for file in files:
            blob = storage.Blob(file.filename, APP_BUCKET)
            blob.upload_from_file(file, blob, content_type=file.mimetype)
            blob.make_public()
            
            image = vision.Image()
            image.source.image_uri = 'gs://' + BUCKET_NAME + '/' + file.filename

            logging.info("image uri: {}".format(image.source.image_uri))

            response = CV_CLIENT.label_detection(image=image)
            labels = response.label_annotations

            logging.info('image_classify: filename={} blob={} classifications={}'\
                .format(file.filename,blob.name,labels))
            results.append(dict(bucket=APP_BUCKET,
                                filename=file.filename,
                                labels=labels))
    
    data = dict(bucket_name=APP_BUCKET.name, 
                min_confidence=min_confidence, 
                results=results)
    return flask.render_template('image_classify_cloud_vision_api.html', data=data)


@app.route('/classification_results')
def classification_results():
    # Retrieve classification results from Firestore
    docs_ref = db.collection('image_classify_results')
    docs = docs_ref.stream()
    
    data = {doc.id: doc.to_dict() for doc in docs}

    return flask.render_template('classification_results.html', data=data, bucket_name=APP_BUCKET.name)


if __name__ == '__main__':
    # When invoked as a prog    logging.info('Starting app')
    host = os.environ.get('APP_HOST', '127.0.0.1')
    app.run(host=host, port=8080, debug=True)

