FROM nikolaik/python-nodejs:python3.8-nodejs12

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN cd src/web && npm install && npm run build
RUN mv src/web/dist static
CMD [ "python", "/app/src/dimsum/dimsum.py" ]
