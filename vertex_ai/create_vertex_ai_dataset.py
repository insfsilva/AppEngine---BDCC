import os
import csv
import requests
from google.cloud import bigquery
from google.cloud import storage


BUCKET_NAME = "bdcc_vertex_ai_bucket"
BQ_CLIENT = bigquery.Client()
STORAGE_CLIENT = storage.Client()

# If bucket doesn't exist create it
if not STORAGE_CLIENT.lookup_bucket(BUCKET_NAME):
    BUCKET = STORAGE_CLIENT.create_bucket(BUCKET_NAME)
else:
    BUCKET = STORAGE_CLIENT.get_bucket(BUCKET_NAME)

csv_file_name = "vertex_ai_dataset.csv"


# Obtain all imageIds associated to the given class
def getImageId(description):
    results = BQ_CLIENT.query(
    '''
        Select ImageId
        FROM `bdcc-project-1-417816.openimages.cl`
            INNER JOIN `bdcc-project-1-417816.openimages.im_lab` USING(Label)
        WHERE Description = '{}'
        LIMIT 100
    '''.format(description)).result()

    image_ids = [row["ImageId"] for row in results]

    return list(image_ids)


# Load images from open_images_dataset from the https URL to the local bucket
def loadImagesToBucket(class_name):
    for i in range(0,len(class_name)):
        response = requests.get("https://storage.googleapis.com/bdcc_open_images_dataset/images/" + class_name[i] + ".jpg")
        blob = BUCKET.blob("images/" + class_name[i] + ".jpg")
        blob.upload_from_string(response.content)


def main():
    # Define classes for vertex ai model training
    classes = ["Bee","Crab","Deer","Eagle","Goose","Horse","Mouse","Parrot","Rabbit","Shark"]

    # Delete .csv file if it already exists
    if os.path.exists(csv_file_name):
        os.remove(csv_file_name)
    
    # Create .csv file
    with open(csv_file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        field = ["Split", "URI", "Class"]
        writer.writerow(field)

        for i in classes:            
            # For each class, get imageIds of all images
            results = getImageId(i)
            
            # Load https image to local bucket (gs://)
            loadImagesToBucket(results)

            # For each image in the class, create a table entry 
            for j in range(0, 100):
                uri = "gs://bdcc_vertex_ai_bucket/images/" + results[j] + ".jpg"
                if j < 80:
                    writer.writerow(["training", uri, i])
                elif j >= 80 and j < 90:
                    writer.writerow(["validation", uri, i])
                else:
                    writer.writerow(["test", uri, i]) 

    # Delete .csv file if it already exists in bucket
    blob = BUCKET.blob(csv_file_name)
    if blob.exists():
        blob.delete()
    
    # Upload .csv file to bucket
    blob.upload_from_filename(csv_file_name)                   
        

if __name__ == '__main__':
    main()