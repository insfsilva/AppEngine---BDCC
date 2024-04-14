docker run --rm -it \
  -e GOOGLE_CLOUD_PROJECT=bdcc-project-1-417816 \
  -e APP_HOST=0.0.0.0 \
  -e GOOGLE_APPLICATION_CREDENTIALS=usr/src/app/key.json \
  -p 8080:8080 \
  -m 2g \
  app
